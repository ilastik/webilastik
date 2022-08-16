#pyright: strict

import asyncio
from enum import Enum
from typing import ClassVar, NewType, Dict, Mapping, List, Sequence, Set, Literal, Tuple
import uuid
from pathlib import PurePosixPath
import datetime

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
        WEBILASTIK_SOURCE_DIR: PurePosixPath,
        CONDA_ENV_DIR: PurePosixPath,
        MODULES_TO_LOAD: Sequence[str],
        EXECUTOR_GETTER_IMPLEMENTATION: Literal["default", "jusuf", "cscs"],
        CACHING_IMPLEMENTATION: Literal["lru_cache",  "no_cache",  "redis_cache"],

        num_nodes: int,
        extra_sbatch_opts: Mapping[str, str] = {},
        extra_environment_vars: Mapping[str, str] = {}
    ) -> None:
        self.user = user
        self.hostname = hostname
        self.account = account
        self.login_node_info = login_node_info

        self.WEBILASTIK_SOURCE_DIR = WEBILASTIK_SOURCE_DIR
        self.CONDA_ENV_DIR = CONDA_ENV_DIR
        self.MODULES_TO_LOAD = MODULES_TO_LOAD
        self.EXECUTOR_GETTER_IMPLEMENTATION = EXECUTOR_GETTER_IMPLEMENTATION
        self.CACHING_IMPLEMENTATION = CACHING_IMPLEMENTATION

        self.num_nodes = num_nodes
        self.extra_sbatch_opts = extra_sbatch_opts
        self.extra_environment_vars = extra_environment_vars
        super().__init__()

    async def do_ssh(self, *, command: str, command_args: List[str]) -> "str | Exception":
        login_node_preamble: List[str] = []
        if self.login_node_info:
            login_node_preamble = [
                "ssh", "-oCheckHostIP=no", "-oBatchMode=yes", f"{self.login_node_info[0]}@{self.login_node_info[1]}",
            ]

        try:
            process = await asyncio.create_subprocess_exec(
                *login_node_preamble,
                "ssh", "-v", "-oBatchMode=yes", f"{self.user}@{self.hostname}",
                "--",
                command,
                *command_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
        except Exception as e:
            return e

        if process.returncode != 0:
            return Exception(stderr.decode())

        return stdout.decode()


    async def launch(
        self,
        *,
        user_info: UserInfo,
        time: Minutes,
        EBRAINS_USER_ACCESS_TOKEN: UserToken,
        SESSION_ID: uuid.UUID,
    ) -> "SlurmJob | Exception":
        env_vars: Dict[str, str] = {
            "WEBILASTIK_SOURCE_DIR": str(self.WEBILASTIK_SOURCE_DIR),
            "CONDA_ENV_DIR": str(self.CONDA_ENV_DIR),
            "SESSION_ID": str(SESSION_ID),
            "MODULES_TO_LOAD": '@'.join(self.MODULES_TO_LOAD),
            "EXECUTOR_GETTER_IMPLEMENTATION": self.EXECUTOR_GETTER_IMPLEMENTATION,
            "CACHING_IMPLEMENTATION": self.CACHING_IMPLEMENTATION,
            "EBRAINS_USER_ACCESS_TOKEN": EBRAINS_USER_ACCESS_TOKEN.access_token,
            **self.extra_environment_vars
        }

        sbatch_args: Dict[str, str] = {
            "--job-name": SlurmJob.make_name(user_info=user_info, session_id=SESSION_ID),
            "--nodes": str(self.num_nodes), #FIXME
            "--ntasks": "2", #FIXME
            "--account": self.account,
            "--time": str(time),
            "--export": ",".join([
                "ALL",
                *[f"{key}={value}" for key, value in env_vars.items()]
            ])
        }

        output_result = await self.do_ssh(
            command="sbatch",
            command_args=[
                *[f"{key}={value}" for key, value in sbatch_args.items()],
               f"{self.WEBILASTIK_SOURCE_DIR}/scripts/launch_webilastik_worker__sbatch.sh",
            ]
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
            WEBILASTIK_SOURCE_DIR=PurePosixPath("/p/project/icei-hbp-2022-0010/source/webilastik"),
            CONDA_ENV_DIR=PurePosixPath("/p/project/icei-hbp-2022-0010/miniconda3/envs/webilastik"),
            MODULES_TO_LOAD=["GCC/11.2.0", "OpenMPI/4.1.2"],
            extra_sbatch_opts={
                "--partition": "batch",
                "--hint": "nomultithread",
            },
            EXECUTOR_GETTER_IMPLEMENTATION="jusuf",
            CACHING_IMPLEMENTATION="redis_cache",
            num_nodes=1,
        )
