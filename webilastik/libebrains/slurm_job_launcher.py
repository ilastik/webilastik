#pyright: strict

from abc import abstractmethod
import asyncio
from enum import Enum
from typing import ClassVar, Dict, Iterable, NewType, List, Set, Tuple
import uuid
import datetime
import textwrap
import tempfile

from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonString

from webilastik.libebrains.user_info import UserInfo
from webilastik.libebrains.user_token import UserToken

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
    NAME_PREFIX: ClassVar[str] = "EBRAINS"

    def __init__(
        self,
        *,
        job_id: SlurmJobId,
        name: str,
        state: JobState,
        start_time_utc_sec: "Seconds | None",
        time_elapsed_sec: "Seconds",
        time_limit_minutes: "Minutes",
        num_nodes: "int",
    ) -> None:
        self.job_id = job_id
        self.state = state
        self.start_time_utc_sec = start_time_utc_sec
        self.time_elapsed_sec = time_elapsed_sec
        self.time_limit_minutes = time_limit_minutes
        self.num_nodes = num_nodes
        self.name = name
        raw_user_sub, raw_session_id = name.split("-user-")[1].split("-session-")
        self.user_sub = uuid.UUID(raw_user_sub)
        self.session_id = uuid.UUID(raw_session_id)
        super().__init__()

    def to_json_value(self) -> JsonObject:
        return {
            "job_id": self.job_id,
            "state": self.state.to_json_value(),
            "start_time_utc_sec": self.start_time_utc_sec,
            "time_elapsed_sec": self.time_elapsed_sec,
            "time_limit_minutes": self.time_limit_minutes,
            "num_nodes": self.num_nodes,
            "name": self.name,
            # "user_sub": self.uuid,
            "session_id": str(self.session_id),
        }

    @classmethod
    def make_name(cls, user_info: UserInfo, session_id: uuid.UUID) -> str:
        return f"{cls.NAME_PREFIX}-user-{user_info.sub}-session-{session_id}"

    @classmethod
    def recognizes_job_name(cls, name: str) -> bool:
        return name.startswith(cls.NAME_PREFIX)

    def is_running(self) -> bool:
        return self.state == JobState.RUNNING

    def is_runnable(self) -> bool:
        return self.state in RUNNABLE_STATES

    def has_failed(self) -> bool:
        return self.state.is_failure()

    def is_done(self) -> bool:
        return self.state.is_done()

    def belongs_to(self, user_info: UserInfo) -> bool:
        return self.user_sub == user_info.sub

    @classmethod
    def compute_used_quota(cls, jobs: Iterable["SlurmJob"]) -> NodeSeconds:
        return NodeSeconds(sum(job.time_elapsed_sec * job.num_nodes for job in jobs))

class SshJobLauncher:
    def __init__(
        self,
        *,
        user: Username,
        hostname: Hostname,
        login_node_info: "Tuple[Username, Hostname] | None" = None,
        account: str,
    ) -> None:
        self.user = user
        self.hostname = hostname
        self.account = account
        self.login_node_info = login_node_info

        super().__init__()

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
        user_info: UserInfo,
        time: Minutes,
        ebrains_user_token: UserToken,
        session_id: uuid.UUID,
    ) -> "SlurmJob | Exception":
        job_name = SlurmJob.make_name(user_info=user_info, session_id=session_id)

        output_result = await self.do_ssh(
            command="sbatch",
            command_args=[f"--job-name={job_name}", f"--time={time}", f"--account={self.account}"],
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

    async def get_job_by_session_id(self, session_id: uuid.UUID, user_info: UserInfo) -> "SlurmJob | None | Exception":
        jobs_result = await self.get_jobs(name=SlurmJob.make_name(session_id=session_id, user_info=user_info))
        if isinstance(jobs_result, Exception):
            return jobs_result
        if len(jobs_result) == 0:
            return None
        return jobs_result[0]

    async def get_jobs(
        self,
        *,
        job_id: "SlurmJobId | None" = None,
        name: "str | None" = None,
        state: "Set[JobState] | None" = None,
        starttime: "datetime.datetime" = datetime.datetime(year=2020, month=1, day=1),
        endtime: "datetime.datetime" = datetime.datetime.today() + datetime.timedelta(days=2), #definetely in the future
        user_info: "UserInfo | None" = None,
    ) -> "List[SlurmJob] | Exception":
        sacct_params = [
            "--allocations", # don't show individual steps
            "--noheader",
            "--parsable2", #items separated with '|'. No trailing '|'
            "--format=JobID,JobName,State,ElapsedRaw,TimelimitRaw,Start,AllocNodes",
            f"--starttime={starttime.year:04d}-{starttime.month:02d}-{starttime.day:02d}",
            f"--endtime={endtime.year:04d}-{endtime.month:02d}-{endtime.day:02d}",
            f"--user={self.user}",
            f"--account={self.account}",
        ]

        if job_id is not None:
            sacct_params.append(f"--jobs={job_id}")
        if name is not None:
            sacct_params.append(f"--name={name}")
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
            raw_id, job_name, raw_state, raw_elapsed, raw_time_limit, raw_start_time_utc_sec, raw_alloc_nodes = line.split("|")
            if not SlurmJob.recognizes_job_name(job_name):
                continue
            job = SlurmJob(
                job_id=SlurmJobId(int(raw_id)),
                name=job_name,
                state=JobState.from_json_value(raw_state.split(" ")[0]),
                start_time_utc_sec=None if raw_start_time_utc_sec == "Unknown" else Seconds(int(raw_start_time_utc_sec)),
                time_elapsed_sec=Seconds(int(raw_elapsed)),
                time_limit_minutes=Minutes(int(raw_time_limit)),
                num_nodes=int(raw_alloc_nodes),
            )
            if user_info and not job.belongs_to(user_info=user_info):
                continue
            jobs.append(job)
        return jobs

    async def get_usage_for_user(self, user_info: UserInfo) -> "NodeSeconds | Exception":
        this_month_jobs_result = await self.get_jobs(starttime=datetime.datetime.today().replace(day=1))
        if isinstance(this_month_jobs_result, Exception):
            return this_month_jobs_result
        node_seconds = sum(
            (job.time_elapsed_sec * job.num_nodes)
            for job in this_month_jobs_result
            if job.user_sub == user_info.sub
        )
        return NodeSeconds(node_seconds)

class JusufSshJobLauncher(SshJobLauncher):
    def __init__(self) -> None:
        super().__init__(
            user=Username("webilastik"),
            hostname=Hostname("jusuf.fz-juelich.de"),
            account="icei-hbp-2022-0010",
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

            export EBRAINS_USER_ACCESS_TOKEN="{ebrains_user_token.access_token}"
            set -xeu

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

            while [ ! -S {redis_unix_socket_path} -o ! -e {redis_pid_file} ]; do
                echo "Redis not ready yet. Sleeping..."
                sleep 1
            done

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
    def __init__(self):
        super().__init__(
            user=Username("bp000188"),
            hostname=Hostname("daint.cscs.ch"),
            login_node_info=(Username("bp000188"), Hostname("ela.cscs.ch")),
            account="ich005",
        )

    def get_sbatch_launch_script(
        self,
        *,
        time: Minutes,
        ebrains_user_token: UserToken,
        session_id: uuid.UUID,
    ) -> str:
        scratch = "/scratch/snx3000/bp000188"
        project = "/users/bp000188"
        webilastik_source_dir = f"{project}/source/webilastik"
        conda_env_dir = f"{project}/miniconda3/envs/webilastik"

        out =  textwrap.dedent(f"""\
            #!/bin/bash
            #SBATCH --nodes=10
            #SBATCH --ntasks=30
            #SBATCH --cpus-per-task=12
            #SBATCH --partition=normal
            #SBATCH --hint=nomultithread
            #SBATCH --constraint=mc

            export EBRAINS_USER_ACCESS_TOKEN="{ebrains_user_token.access_token}"
            set -xeu

            # prevent numpy from spawning its own threads
            export OPENBLAS_NUM_THREADS=1
            export MKL_NUM_THREADS=1

            PYTHONPATH="{webilastik_source_dir}"
            PYTHONPATH+=":{webilastik_source_dir}/executor_getters/cscs/"
            PYTHONPATH+=":{webilastik_source_dir}/caching/lru_cache/"

            export PYTHONPATH
            export LRU_CACHE_MAX_SIZE=512
            export EBRAINS_USER_ACCESS_TOKEN="{ebrains_user_token.access_token}"

            srun -n 30\\
                "{conda_env_dir}/bin/python" {webilastik_source_dir}/webilastik/ui/workflow/ws_pixel_classification_workflow.py \\
                --max-duration-minutes={time} \\
                --ebrains-user-access-token={ebrains_user_token.access_token} \\
                --listen-socket="{scratch}/to-master-{session_id}" \\
                --session-url=https://app.ilastik.org/session-{session_id} \\
                tunnel \\
                --remote-username=www-data \\
                --remote-host=app.ilastik.org \\
                --remote-unix-socket="/tmp/to-session-{session_id}" \\
        """)
        # print(out)
        return out