#pyright: strict

from abc import abstractmethod
import asyncio
from enum import Enum
from subprocess import Popen
from typing import Dict, Iterable, NewType, List, Set, Tuple
import uuid
import datetime
import textwrap
import tempfile
import json
from pathlib import Path
import getpass
import sys
import os

from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString
from cryptography.fernet import Fernet
from webilastik.libebrains.oidc_client import OidcClient

from webilastik.libebrains.user_info import UserInfo
from webilastik.libebrains.user_token import UserToken

_oidc_client = OidcClient.from_environment()

class JobState(Enum):
    BOOT_FAIL = "BOOT_FAIL"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    DEADLINE = "DEADLINE"
    FAILED = "FAILED"
    NODE_FAIL = "NODE_FAIL"
    OUT_OF_MEMORY = "OUT_OF_MEMORY"
    PENDING = "PENDING"
    PREEMPTED = "PREEMPTED"
    RUNNING = "RUNNING"
    REQUEUED = "REQUEUED"
    RESIZING = "RESIZING"
    REVOKED = "REVOKED"
    SUSPENDED = "SUSPENDED"
    TIMEOUT = "TIMEOUT"

    def is_failure(self) -> bool:
        return self in FAILED_STATES

    def is_done(self) -> bool:
        return self in DONE_STATES

    def to_json_value(self) -> str:
        return self.value

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "JobState":
        value_str = ensureJsonString(value)
        for state in JobState:
            if state.value == value_str:
                return state
        raise ValueError(f"Bad job state: {value_str}")

FAILED_STATES = set([
    JobState.BOOT_FAIL,
    JobState.CANCELLED,
    JobState.DEADLINE,
    JobState.FAILED,
    JobState.NODE_FAIL,
    JobState.OUT_OF_MEMORY,
    JobState.PREEMPTED,
    JobState.REVOKED,
    JobState.TIMEOUT,
])

DONE_STATES = set([JobState.COMPLETED]).union(FAILED_STATES)

RUNNABLE_STATES = set([
    JobState.PENDING,
    JobState.RUNNING,
    JobState.REQUEUED,
    JobState.RESIZING,
    JobState.SUSPENDED,
])


Username = NewType("Username", str)
Hostname = NewType("Hostname", str)
Minutes = NewType("Minutes", int)
Seconds = NewType("Seconds", int)
SlurmJobId = NewType("SlurmJobId", int)
NodeSeconds = NewType("NodeSeconds", int)

class SlurmJob:
    SACCT_FORMAT_ITEMS = ["JobID", "JobName", "State", "ElapsedRaw", "TimelimitRaw", "Start", "AllocNodes"]

    @classmethod
    def try_from_parsable2_raw_job_data(cls, parsable2_raw_job_data: str, fernet: Fernet) -> "SlurmJob | None | Exception":
        items = parsable2_raw_job_data.split("|")
        try:
            raw_id, job_name, raw_state, raw_elapsed, raw_time_limit, raw_start_time_utc_sec, raw_alloc_nodes = items
        except Exception as e:
            return Exception(f"Bad number of raw job parameters: {e}")

        # discard old jobs for now
        if job_name.startswith("EBRAINS"):
            return None

        try:
            metadata_json = fernet.decrypt(job_name.encode('utf8'))
        except Exception as e:
            return None
        try:
            metadata = json.loads(metadata_json)
        except Exception as e:
            return Exception(f"Could not interpret metadata comment as json: {metadata_json}")

        try:
            metadata_obj = ensureJsonObject(metadata)
            user_id = uuid.UUID(ensureJsonString(metadata_obj.get("uid")))
            session_id = uuid.UUID(ensureJsonString(metadata_obj.get("sid")))
        except Exception as e:
            return Exception(f"Bad metadata json: {metadata_json}")

        return SlurmJob(
            job_id=SlurmJobId(int(raw_id)),
            state=JobState.from_json_value(raw_state.split(" ")[0]),
            start_time_utc_sec=None if raw_start_time_utc_sec == "Unknown" else Seconds(int(raw_start_time_utc_sec)),
            time_elapsed_sec=Seconds(int(raw_elapsed)),
            time_limit_minutes=Minutes(int(raw_time_limit)),
            num_nodes=int(raw_alloc_nodes),
            user_id=user_id,
            session_id=session_id,
        )

    @classmethod
    def make_job_name(
        cls, *, user_id: uuid.UUID, session_id: uuid.UUID, fernet: Fernet
    ) -> str:
        comment_data = {
            "uid": str(user_id),
            "sid": str(session_id),
        }
        return fernet.encrypt(
            json.dumps(comment_data, separators=(',', ':')).encode('utf8'),
        ).decode('utf8')

    def __init__(
        self,
        *,
        job_id: SlurmJobId,
        state: JobState,
        start_time_utc_sec: "Seconds | None",
        time_elapsed_sec: "Seconds",
        time_limit_minutes: "Minutes",
        num_nodes: int,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> None:
        self.job_id = job_id
        self.state = state
        self.start_time_utc_sec = start_time_utc_sec
        self.time_elapsed_sec = time_elapsed_sec
        self.time_limit_minutes = time_limit_minutes
        self.num_nodes = num_nodes
        self.user_id = user_id
        self.session_id = session_id
        super().__init__()


    def to_json_value(self) -> JsonObject:
        return {
            "job_id": self.job_id,
            "state": self.state.to_json_value(),
            "start_time_utc_sec": self.start_time_utc_sec,
            "time_elapsed_sec": self.time_elapsed_sec,
            "time_limit_minutes": self.time_limit_minutes,
            "num_nodes": self.num_nodes,
            # "user_sub": self.uuid,
            "session_id": str(self.session_id),
        }

    def is_running(self) -> bool:
        return self.state == JobState.RUNNING

    def is_runnable(self) -> bool:
        return self.state in RUNNABLE_STATES

    def has_failed(self) -> bool:
        return self.state.is_failure()

    def is_done(self) -> bool:
        return self.state.is_done()

    def belongs_to(self, user_info: UserInfo) -> bool:
        return self.user_id == user_info.sub

    @classmethod
    def compute_used_quota(cls, jobs: Iterable["SlurmJob"]) -> NodeSeconds:
        return NodeSeconds(sum(job.time_elapsed_sec * job.num_nodes for job in jobs))

class SshJobLauncher:
    JOB_NAME_PREFIX = "EBRAINS"

    def __init__(
        self,
        *,
        user: Username,
        hostname: Hostname,
        login_node_info: "Tuple[Username, Hostname] | None" = None,
        account: str,
        fernet: Fernet,
    ) -> None:
        self.user = user
        self.hostname = hostname
        self.account = account
        self.fernet = fernet
        self.login_node_info = login_node_info

        super().__init__()

    @classmethod
    def make_job_name(cls, user_id: uuid.UUID) -> str:
        return f"{cls.JOB_NAME_PREFIX}-{user_id}"

    async def do_ssh(
        self,
        *,
        command: str,
        command_args: List[str],
        environment: "Dict[str, str] | None" = None,
        stdin: "str | None" = None,
    ) -> "str | Exception":
        environment_preamble = ""
        if environment:
            environment_preamble = " ".join([f"{key}={value}" for key, value in environment.items()])

        login_node_preamble: List[str] = []
        if self.login_node_info:
            login_node_preamble = [
                "ssh", "-oCheckHostIP=no", "-oBatchMode=yes", f"{self.login_node_info[0]}@{self.login_node_info[1]}",
            ]

        if stdin:
            stdin_file = tempfile.TemporaryFile()
            stdin_contents = stdin.encode('utf8')
            num_bytes_written = stdin_file.write(stdin_contents)
            if num_bytes_written != len(stdin_contents):
                return Exception(f"Could not write sbatch script to temp file")
            _ = stdin_file.seek(0)
        else:
            stdin_file = None

        try:
            process = await asyncio.create_subprocess_exec(
                *login_node_preamble,
                "ssh", "-v", "-oBatchMode=yes", f"{self.user}@{self.hostname}",
                "--",
                f"{environment_preamble} {command} " + " ".join(command_args),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=stdin_file,
            )
            stdout, stderr = await process.communicate()
        except Exception as e:
            return e

        if process.returncode != 0:
            return Exception(stderr.decode())

        return stdout.decode()


    @abstractmethod
    def get_sbatch_launch_script(
        self,
        *,
        time: Minutes,
        ebrains_user_token: UserToken,
        session_id: uuid.UUID,
    ) -> "str":
        pass

    async def launch(
        self,
        *,
        user_id: uuid.UUID,
        time: Minutes,
        ebrains_user_token: UserToken,
        session_id: uuid.UUID,
        display_name: str = ""
    ) -> "SlurmJob | Exception":
        output_result = await self.do_ssh(
            command="sbatch",
            command_args=[
                f"--job-name={SlurmJob.make_job_name(user_id=user_id, session_id=session_id, fernet=self.fernet)}",
                f"--time={time}",
                f"--account={self.account}",
            ],
            stdin=self.get_sbatch_launch_script(
                time=time,
                ebrains_user_token=ebrains_user_token,
                session_id=session_id,
            ),
        )
        if isinstance(output_result, Exception):
            return output_result

        job_id = SlurmJobId(int(output_result.split()[3]))

        for _ in range(5):
            await asyncio.sleep(0.7)
            job = await self.get_job_by_slurm_id(job_id=job_id)
            if isinstance(job, (Exception, SlurmJob)):
                return job
        return Exception(f"Could not retrieve job with id {job_id}")


    async def cancel(self, job: SlurmJob) -> "Exception | None":
        result = await self.do_ssh(command="scancel", command_args=[str(job.job_id)])
        if isinstance(result, Exception):
            return result
        return None

    async def get_current_job_for_user(self, user_info: UserInfo) -> "SlurmJob | None | Exception":
        runnable_jobs_result = await self.get_jobs(state=RUNNABLE_STATES)
        if isinstance(runnable_jobs_result, Exception):
            return runnable_jobs_result
        for job in runnable_jobs_result:
            if job.belongs_to(user_info=user_info):
                return job
        return None

    async def get_job_by_slurm_id(self, job_id: SlurmJobId) -> "SlurmJob | None | Exception":
        jobs_result = await self.get_jobs(job_id=job_id)
        if isinstance(jobs_result, Exception):
            return jobs_result
        if len(jobs_result) == 0:
            return None
        return jobs_result[0]

    async def get_job_by_session_id(self, session_id: uuid.UUID, user_id: uuid.UUID) -> "SlurmJob | None | Exception":
        jobs_result = await self.get_jobs(user_id=user_id)
        if isinstance(jobs_result, Exception):
            return jobs_result
        for job in jobs_result:
            if job.session_id == session_id:
                return job
        return None

    async def get_jobs(
        self,
        *,
        job_id: "SlurmJobId | None" = None,
        state: "Set[JobState] | None" = None,
        starttime: "datetime.datetime" = datetime.datetime(year=2020, month=1, day=1),
        endtime: "datetime.datetime | None" = None,
        user_id: "uuid.UUID | None" = None,
        session_id: "uuid.UUID | None" = None,
    ) -> "List[SlurmJob] | Exception":
        endtime = endtime or datetime.datetime.today() + datetime.timedelta(days=2) # definetely in the future
        sacct_params = [
            "--allocations", # don't show individual steps
            "--noheader",
            "--parsable2", #items separated with '|'. No trailing '|'
            f"--format={','.join(SlurmJob.SACCT_FORMAT_ITEMS)}",
            f"--starttime={starttime.year:04d}-{starttime.month:02d}-{starttime.day:02d}",
            f"--endtime={endtime.year:04d}-{endtime.month:02d}-{endtime.day:02d}",
            f"--user={self.user}",
            f"--account={self.account}",
        ]

        if job_id is not None:
            sacct_params.append(f"--jobs={job_id}")
        if state != None and len(state) > 0:
            sacct_params.append(f"--state={','.join(s.value for s in state)}")

        output_result = await self.do_ssh(
            environment={"SLURM_TIME_FORMAT": r"%s"},
            command="sacct",
            command_args=sacct_params
        )
        if isinstance(output_result, Exception):
            return output_result
        jobs: List[SlurmJob] = []
        for line in output_result.split("\n")[:-1]: #skip empty newline
            job_result = SlurmJob.try_from_parsable2_raw_job_data(line, fernet=self.fernet)
            if isinstance(job_result, Exception):
                return job_result
            if job_result is None:
                continue
            if user_id and job_result.user_id != user_id:
                continue
            if session_id and job_result.session_id == session_id:
                return [job_result]
            jobs.append(job_result)
        return jobs

class LocalJobLauncher(SshJobLauncher):
    def __init__(
        self,
        *,
        user: Username = Username(getpass.getuser()),
        fernet: Fernet,
    ) -> None:
        super().__init__(
            user=user,
            hostname=Hostname("localhost"),
            account="dummy",
            fernet=fernet,
        )
        self.jobs: Dict[SlurmJobId, Tuple[SlurmJob, Popen[bytes]]] = {}

    def get_sbatch_launch_script(
        self,
        *,
        time: Minutes,
        ebrains_user_token: UserToken,
        session_id: uuid.UUID,
    ) -> str:
        working_dir = f"/tmp/{session_id}"
        webilastik_source_dir = Path(__file__).parent.parent.parent
        redis_pid_file = f"{working_dir}/redis.pid"
        redis_unix_socket_path = f"{working_dir}/redis.sock"
        conda_env_dir = Path(os.path.realpath(sys.executable)).parent.parent

        return textwrap.dedent(f"""
            #!/bin/bash -l

            export {UserToken.EBRAINS_USER_ACCESS_TOKEN_ENV_VAR_NAME}="{ebrains_user_token.access_token}"
            export {UserToken.EBRAINS_USER_REFRESH_TOKEN_ENV_VAR_NAME}="{ebrains_user_token.refresh_token}"
            export EBRAINS_CLIENT_ID="{_oidc_client.client_id}"
            export EBRAINS_CLIENT_SECRET="{_oidc_client.client_secret}"
            set -xeu
            set -o pipefail

            mkdir {working_dir}
            cd {working_dir}

            # prevent numpy from spawning its own threads
            export OPENBLAS_NUM_THREADS=1
            export MKL_NUM_THREADS=1

            test -x {conda_env_dir}/bin/redis-server
            {conda_env_dir}/bin/redis-server \\
                --pidfile {redis_pid_file} \\
                --unixsocket {redis_unix_socket_path} \\
                --unixsocketperm 777 \\
                --port 0 \\
                --daemonize no \\
                --maxmemory-policy allkeys-lru \\
                --maxmemory 10gb \\
                --appendonly no \\
                --save "" \\
                --dir {working_dir} \\
                &

            NUM_TRIES=10;
            while [ ! -e {redis_pid_file} -a $NUM_TRIES -gt 0 ]; do
                echo "Redis not ready yet. Sleeping..."
                NUM_TRIES=$(expr $NUM_TRIES - 1)
                sleep 1
            done

            if [ $NUM_TRIES -eq 0 ]; then
                echo "Could not start redis"
                exit 1
            fi

            PYTHONPATH="{webilastik_source_dir}"
            PYTHONPATH+=":{webilastik_source_dir}/ndstructs/"
            PYTHONPATH+=":{webilastik_source_dir}/executor_getters/default/"
            PYTHONPATH+=":{webilastik_source_dir}/caching/redis_cache/"

            export PYTHONPATH
            export REDIS_UNIX_SOCKET_PATH="{redis_unix_socket_path}"

            "{conda_env_dir}/bin/python" {webilastik_source_dir}/webilastik/ui/workflow/ws_pixel_classification_workflow.py \\
                --max-duration-minutes={time} \\
                --listen-socket="{working_dir}/to-master.sock" \\
                --session-url=https://app.ilastik.org/session-{session_id} \\
                tunnel \\
                --remote-username=www-data \\
                --remote-host=app.ilastik.org \\
                --remote-unix-socket="/tmp/to-session-{session_id}" \\

            kill -2 $(cat {redis_pid_file})
            sleep 2
        """)

    async def launch(
        self,
        *,
        user_id: uuid.UUID,
        time: Minutes,
        ebrains_user_token: UserToken,
        session_id: uuid.UUID,
        display_name: str = ""
    ) -> "SlurmJob | Exception":
        stdin_file = tempfile.TemporaryFile()
        _ = stdin_file.write(
            self.get_sbatch_launch_script(
                time=time, ebrains_user_token=ebrains_user_token, session_id=session_id
            ).encode("utf8")
        )
        _ = stdin_file.seek(0)

        session_process = Popen(["bash"], stdin=stdin_file, start_new_session=True)
        job_id = SlurmJobId(len(self.jobs))
        dummy_slurm_job = SlurmJob(
            job_id=job_id,
            state=JobState.RUNNING,
            start_time_utc_sec=Seconds(int(datetime.datetime.now(datetime.timezone.utc).timestamp())),
            time_elapsed_sec=Seconds(1),
            num_nodes=1, #FIXME
            session_id=session_id,
            time_limit_minutes=time,
            user_id=user_id,
        )
        self.jobs[job_id] = (dummy_slurm_job, session_process)

        return dummy_slurm_job

    async def cancel(self, job: SlurmJob) -> "Exception | None":
        self.jobs[job.job_id][1].kill()
        self.jobs[job.job_id][0].state = JobState.CANCELLED
        return None

    async def get_jobs(
        self,
        *,
        job_id: "SlurmJobId | None" = None,
        state: "Set[JobState] | None" = None,
        starttime: "datetime.datetime" = datetime.datetime(year=2020, month=1, day=1),
        endtime: "datetime.datetime | None" = None,
        user_id: "uuid.UUID | None" = None,
        session_id: "uuid.UUID | None" = None,
    ) -> "List[SlurmJob] | Exception":
        jobs: List[SlurmJob] = []
        for job_item_id, (slurm_job_item, _) in self.jobs.items():
            if job_id and job_id == job_item_id:
                return [slurm_job_item]
            if session_id and slurm_job_item.session_id == session_id:
                return [slurm_job_item]
            if user_id and slurm_job_item.user_id != user_id:
                continue
            if state and slurm_job_item.state not in state:
                continue
            if slurm_job_item.start_time_utc_sec and slurm_job_item.start_time_utc_sec < starttime.timestamp():
                continue
            #FIXME: endtime?
            jobs.append(slurm_job_item)
        return jobs


class JusufSshJobLauncher(SshJobLauncher):
    def __init__(self, fernet: Fernet) -> None:
        super().__init__(
            user=Username("webilastik"),
            hostname=Hostname("jusuf.fz-juelich.de"),
            account="icei-hbp-2022-0010",
            fernet=fernet,
        )

    def get_sbatch_launch_script(
        self,
        *,
        time: Minutes,
        ebrains_user_token: UserToken,
        session_id: uuid.UUID,
    ) -> str:
        working_dir = f"$SCRATCH/{session_id}"
        home="/p/home/jusers/webilastik/jusuf"
        webilastik_source_dir = f"{working_dir}/webilastik"
        conda_env_dir = f"{home}/miniconda3/envs/webilastik"
        redis_pid_file = f"{working_dir}/redis.pid"
        redis_unix_socket_path = f"{working_dir}/redis.sock"

        return textwrap.dedent(f"""\
            #!/bin/bash -l
            #SBATCH --nodes=1
            #SBATCH --ntasks=2
            #SBATCH --partition=batch
            #SBATCH --hint=nomultithread

            export {UserToken.EBRAINS_USER_ACCESS_TOKEN_ENV_VAR_NAME}="{ebrains_user_token.access_token}"
            export {UserToken.EBRAINS_USER_REFRESH_TOKEN_ENV_VAR_NAME}="{ebrains_user_token.refresh_token}"
            export EBRAINS_CLIENT_ID="{_oidc_client.client_id}"
            export EBRAINS_CLIENT_SECRET="{_oidc_client.client_secret}"
            set -xeu
            set -o pipefail

            jutil env activate -p icei-hbp-2022-0010
            module load git
            module load GCC/11.2.0
            module load OpenMPI/4.1.2

            mkdir {working_dir}
            cd {working_dir}
            # FIXME: download from github when possible
            git clone --depth 1 --branch experimental {home}/webilastik.git {webilastik_source_dir}

            # prevent numpy from spawning its own threads
            export OPENBLAS_NUM_THREADS=1
            export MKL_NUM_THREADS=1

            test -x {conda_env_dir}/bin/redis-server
            srun -n 1 --overlap -u --cpu_bind=none --cpus-per-task 6 \\
                {conda_env_dir}/bin/redis-server \\
                --pidfile {redis_pid_file} \\
                --unixsocket {redis_unix_socket_path} \\
                --unixsocketperm 777 \\
                --port 0 \\
                --daemonize no \\
                --maxmemory-policy allkeys-lru \\
                --maxmemory 100gb \\
                --appendonly no \\
                --save "" \\
                --dir {working_dir} \\
                &

            NUM_TRIES=10;
            while [ ! -e {redis_pid_file} -a $NUM_TRIES -gt 0 ]; do
                echo "Redis not ready yet. Sleeping..."
                NUM_TRIES=$(expr $NUM_TRIES - 1)
                sleep 1
            done

            if [ $NUM_TRIES -eq 0 ]; then
                echo "Could not start redis"
                exit 1
            fi

            PYTHONPATH="{webilastik_source_dir}"
            PYTHONPATH+=":{webilastik_source_dir}/executor_getters/jusuf/"
            PYTHONPATH+=":{webilastik_source_dir}/caching/redis_cache/"

            export PYTHONPATH
            export REDIS_UNIX_SOCKET_PATH="{redis_unix_socket_path}"

            srun -n 1 --overlap -u --cpus-per-task 120 \\
                "{conda_env_dir}/bin/python" {webilastik_source_dir}/webilastik/ui/workflow/ws_pixel_classification_workflow.py \\
                --max-duration-minutes={time} \\
                --listen-socket="{working_dir}/to-master.sock" \\
                --session-url=https://app.ilastik.org/session-{session_id} \\
                tunnel \\
                --remote-username=www-data \\
                --remote-host=app.ilastik.org \\
                --remote-unix-socket="/tmp/to-session-{session_id}" \\

            kill -2 $(cat {redis_pid_file}) #FXME: this only works because it's a single node
            sleep 2
        """)

class CscsSshJobLauncher(SshJobLauncher):
    def __init__(self, fernet: Fernet):
        super().__init__(
            user=Username("bp000188"),
            hostname=Hostname("daint.cscs.ch"),
            login_node_info=(Username("bp000188"), Hostname("ela.cscs.ch")),
            account="ich005",
            fernet=fernet,
        )

    def get_sbatch_launch_script(
        self,
        *,
        time: Minutes,
        ebrains_user_token: UserToken,
        session_id: uuid.UUID,
    ) -> str:
        working_dir = f"$SCRATCH/{session_id}"
        home="/users/bp000188"
        webilastik_source_dir = f"{working_dir}/webilastik"
        conda_env_dir = f"{home}/miniconda3/envs/webilastik"
        redis_pid_file = f"{working_dir}/redis.pid"
        redis_port = "6379"
        num_nodes = 10

        out =  textwrap.dedent(f"""\
            #!/bin/bash
            #SBATCH --nodes={num_nodes}
            #SBATCH --ntasks-per-node=2
            #SBATCH --partition=normal
            #SBATCH --hint=nomultithread
            #SBATCH --constraint=mc

            export {UserToken.EBRAINS_USER_ACCESS_TOKEN_ENV_VAR_NAME}="{ebrains_user_token.access_token}"
            export {UserToken.EBRAINS_USER_REFRESH_TOKEN_ENV_VAR_NAME}="{ebrains_user_token.refresh_token}"
            export EBRAINS_CLIENT_ID="{_oidc_client.client_id}"
            export EBRAINS_CLIENT_SECRET="{_oidc_client.client_secret}"
            set -xeu
            set -o pipefail

            mkdir {working_dir}
            cd {working_dir}
            git clone --depth 1 --branch experimental https://github.com/ilastik/webilastik {webilastik_source_dir}

            # prevent numpy from spawning its own threads
            export OPENBLAS_NUM_THREADS=1
            export MKL_NUM_THREADS=1

            REDIS_IP=$(ip -o addr show ipogif0 | grep -E '\\binet\\b' | awk '{{print $4}}' | cut -d/ -f1)

            test -x {conda_env_dir}/bin/redis-server
            srun --nodes=1-1 --ntasks 1 -u --cpu_bind=none \\
                {conda_env_dir}/bin/redis-server \\
                --pidfile {redis_pid_file} \\
                --bind $REDIS_IP \\
                --port {redis_port} \\
                --daemonize no \\
                --maxmemory-policy allkeys-lru \\
                --maxmemory 48gb \\
                --appendonly no \\
                --save "" \\
                --dir {working_dir} \\
                &

            NUM_TRIES=10;
            while [ ! -e {redis_pid_file} -a $NUM_TRIES -gt 0 ]; do
                echo "Redis not ready yet. Sleeping..."
                NUM_TRIES=$(expr $NUM_TRIES - 1)
                sleep 1
            done

            if [ $NUM_TRIES -eq 0 ]; then
                echo "Could not start redis"
                exit 1
            fi

            PYTHONPATH="{webilastik_source_dir}"
            PYTHONPATH+=":{webilastik_source_dir}/executor_getters/cscs/"
            PYTHONPATH+=":{webilastik_source_dir}/caching/redis_cache/"

            export PYTHONPATH
            export REDIS_HOST_PORT="$REDIS_IP:{redis_port}"

            srun -N {num_nodes - 1} \\
                "{conda_env_dir}/bin/python" {webilastik_source_dir}/webilastik/ui/workflow/ws_pixel_classification_workflow.py \\
                --max-duration-minutes={time} \\
                --listen-socket="{working_dir}/to-master.sock" \\
                --session-url=https://app.ilastik.org/session-{session_id} \\
                tunnel \\
                --remote-username=www-data \\
                --remote-host=app.ilastik.org \\
                --remote-unix-socket="/tmp/to-session-{session_id}" \\

            kill -2 $(cat {redis_pid_file})
            sleep 2
        """)
        # print(out)
        return out