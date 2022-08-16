#pyright: strict

from abc import abstractmethod
import asyncio
from enum import Enum
from typing import ClassVar, NewType, List, Set, Tuple
import uuid
import datetime
import textwrap
import tempfile

from ndstructs.utils.json_serializable import JsonValue, ensureJsonString

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

DONE_STATES = set([
    JobState.BOOT_FAIL,
    JobState.CANCELLED,
    JobState.COMPLETED,
    JobState.DEADLINE,
    JobState.FAILED,
    JobState.NODE_FAIL,
    JobState.OUT_OF_MEMORY,
    JobState.PREEMPTED,
    JobState.REVOKED,
    JobState.TIMEOUT,
])

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
        duration: "Seconds",
        num_nodes: "int",
    ) -> None:
        self.job_id = job_id
        self.state = state
        self.duration = duration
        self.num_nodes = num_nodes
        self.name = name
        raw_user_sub, raw_session_id = name.split("-user-")[1].split("-session-")
        self.user_sub = uuid.UUID(raw_user_sub)
        self.sesson_id = uuid.UUID(raw_session_id)
        super().__init__()

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

    def belongs_to(self, user_info: UserInfo) -> bool:
        return self.user_sub == user_info.sub

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
        self, *, command: str, command_args: List[str], stdin: "str | None" = None
    ) -> "str | Exception":
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
                command,
                *command_args,
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
    ) -> "List[SlurmJob] | Exception":
        sacct_params = [
            "--allocations", # don't show individual steps
            "--noheader",
            "--parsable2", #items separated with '|'. No trailing '|'
            "--format=JobID,JobName,State,ElapsedRaw,AllocNodes",
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

        output_result = await self.do_ssh(command="sacct", command_args=sacct_params)
        if isinstance(output_result, Exception):
            return output_result

        jobs: List[SlurmJob] = []
        for line in output_result.split("\n")[:-1]: #skip empty newline
            raw_id, job_name, raw_state, raw_elapsed, raw_alloc_nodes = line.split("|")
            if not SlurmJob.recognizes_job_name(job_name):
                continue
            jobs.append(
                SlurmJob(
                    job_id=SlurmJobId(int(raw_id)),
                    name=job_name,
                    state=JobState.from_json_value(raw_state.split(" ")[0]),
                    duration=Seconds(int(raw_elapsed)),
                    num_nodes=int(raw_alloc_nodes),
                )
            )
        return jobs

    async def get_usage_for_user(self, user_info: UserInfo) -> "NodeSeconds | Exception":
        this_month_jobs_result = await self.get_jobs(starttime=datetime.datetime.today().replace(day=1))
        if isinstance(this_month_jobs_result, Exception):
            return this_month_jobs_result
        node_seconds = sum(
            (job.duration * job.num_nodes)
            for job in this_month_jobs_result
            if job.user_sub == user_info.sub
        )
        return NodeSeconds(node_seconds)

class JusufSshJobLauncher(SshJobLauncher):
    def __init__(self) -> None:
        super().__init__(
            user=Username("vieira2"),
            hostname=Hostname("jusuf.fz-juelich.de"),
            account="icei-hbp-2022-0010",
        )

    def get_sbatch_launch_script(
        self,
        *,
        ebrains_user_token: UserToken,
        session_id: uuid.UUID,
    ) -> str:
        project = "/p/project/icei-hbp-2022-0010"
        webilastik_source_dir = f"{project}/source/webilastik"
        conda_env_dir = f"{project}/miniconda3/envs/webilastik"
        redis_pid_file = f"{project}/redis-{session_id}.pid"
        redis_unix_socket_path = f"{project}/redis-{session_id}.sock"

        return textwrap.dedent(f"""\
            #!/bin/bash
            #SBATCH --nodes=1
            #SBATCH --ntasks=2
            #SBATCH --partition=batch
            #SBATCH --hint=nomultithread

            set -xeu

            # prevent numpy from spawning its own threads
            export OPENBLAS_NUM_THREADS=1
            export MKL_NUM_THREADS=1

            module load GCC/11.2.0
            module load OpenMPI/4.1.2


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
                --dir {project} \\
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
                --ebrains-user-access-token={ebrains_user_token.access_token} \\
                --listen-socket="{project}/to-master-{session_id}" \\
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
        ebrains_user_token: UserToken,
        session_id: uuid.UUID,
    ) -> str:
        scratch = "/scratch/snx3000/bp000188"
        project = "/users/bp000188"
        webilastik_source_dir = f"{project}/source/webilastik"
        conda_env_dir = f"{project}/miniconda3/envs/webilastik"
        redis_pid_file = f"{scratch}/redis-{session_id}.pid"
        redis_unix_socket_path = f"{scratch}/redis-{session_id}.sock"

        out =  textwrap.dedent(f"""\
            #!/bin/bash
            #SBATCH --nodes=1
            #SBATCH --ntasks=2
            #SBATCH --partition=debug
            #SBATCH --hint=nomultithread
            #SBATCH --constraint=mc

            set -xeu

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
                --dir {scratch} \\
                &

            while [ ! -S {redis_unix_socket_path} -o ! -e {redis_pid_file} ]; do
                echo "Redis not ready yet. Sleeping..."
                sleep 1
            done

            PYTHONPATH="{webilastik_source_dir}"
            PYTHONPATH+=":{webilastik_source_dir}/executor_getters/cscs/"
            PYTHONPATH+=":{webilastik_source_dir}/caching/redis_cache/"

            export PYTHONPATH
            export REDIS_UNIX_SOCKET_PATH="{redis_unix_socket_path}"

            srun -n 1 --overlap -u --cpus-per-task 30 \\
                "{conda_env_dir}/bin/python" {webilastik_source_dir}/webilastik/ui/workflow/ws_pixel_classification_workflow.py \\
                --ebrains-user-access-token={ebrains_user_token.access_token} \\
                --listen-socket="{scratch}/to-master-{session_id}" \\
                tunnel \\
                --remote-username=www-data \\
                --remote-host=app.ilastik.org \\
                --remote-unix-socket="/tmp/to-session-{session_id}" \\

            kill -2 $(cat {redis_pid_file}) #FXME: this only works because it's a single node
            sleep 2
        """)
        # print(out)
        return out