#pyright: strict

import asyncio
from enum import Enum
from typing import ClassVar, NewType, Dict, Mapping, List, Sequence, Set, Literal
import uuid
from pathlib import PurePosixPath
import json
from datetime import datetime

from ndstructs.utils.json_serializable import JsonValue, ensureJsonArray, ensureJsonInt, ensureJsonObject, ensureJsonString

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
        duration: "Seconds | None",
        num_nodes: "int | None",
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
    def recognizes_raw_job(cls, raw_job: JsonValue) -> bool:
        name = ensureJsonString(ensureJsonObject(raw_job).get("name"))
        return name.startswith(cls.NAME_PREFIX)

    def is_running(self) -> bool:
        return self.state == JobState.RUNNING

    def is_runnable(self) -> bool:
        return self.state in RUNNABLE_STATES

    def belongs_to(self, user_info: UserInfo) -> bool:
        return self.user_sub == user_info.sub

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "SlurmJob":
        value_obj = ensureJsonObject(value)
        job_id = SlurmJobId(ensureJsonInt(value_obj.get("job_id")))
        raw_state = ensureJsonObject(value_obj.get("state"))
        state = JobState.from_json_value(raw_state.get("current"))

        if state.is_done():
            time_obj = ensureJsonObject(value_obj["time"])
            start = ensureJsonInt(time_obj["start"])
            end = ensureJsonInt(time_obj["end"])
            duration = Seconds(end - start)
        else:
            duration = None

        tres_resources = ensureJsonObject(value_obj.get("tres"))
        raw_allocated_resources = ensureJsonArray(tres_resources.get("allocated"))
        for raw_resource in raw_allocated_resources:
            resource_obj = ensureJsonObject(raw_resource)
            resource_type = ensureJsonString(resource_obj.get("type"))
            if resource_type == "node":
                num_nodes = ensureJsonInt(resource_obj.get("count"))
                break
        else:
            num_nodes = None

        return SlurmJob(
            job_id=job_id,
            name=ensureJsonString(value_obj.get("name")),
            state=state,
            duration=duration,
            num_nodes=num_nodes,
        )


class SshJobLauncher:
    def __init__(
        self,
        *,
        user: str,
        hostname: str,
        account: str,
        WEBILASTIK_SOURCE_DIR: PurePosixPath,
        CONDA_ENV_DIR: PurePosixPath,
        MODULES_TO_LOAD: Sequence[str],
        EXECUTOR_GETTER_IMPLEMENTATION: Literal["default", "jusuf"],
        CACHING_IMPLEMENTATION: Literal["lru_cache",  "no_cache",  "redis_cache"],

        extra_sbatch_opts: Mapping[str, str] = {},
        extra_environment_vars: Mapping[str, str] = {}
    ) -> None:
        self.user = user
        self.hostname = hostname
        self.account = account

        self.WEBILASTIK_SOURCE_DIR = WEBILASTIK_SOURCE_DIR
        self.CONDA_ENV_DIR = CONDA_ENV_DIR
        self.MODULES_TO_LOAD = MODULES_TO_LOAD
        self.EXECUTOR_GETTER_IMPLEMENTATION = EXECUTOR_GETTER_IMPLEMENTATION
        self.CACHING_IMPLEMENTATION = CACHING_IMPLEMENTATION

        self.extra_sbatch_opts = extra_sbatch_opts
        self.extra_environment_vars = extra_environment_vars
        super().__init__()

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
            "--nodes": "1", #FIXME
            "--ntasks": "2", #FIXME
            "--account": self.account,
            "--time": str(time),
            "--export": ",".join([
                "ALL",
                *[f"{key}={value}" for key, value in env_vars.items()]
            ])
        }

        try:
            process = await asyncio.create_subprocess_exec(
                "ssh", "-v", "-oBatchMode=yes", f"{self.user}@{self.hostname}",
                "--",
                "sbatch",
                *[f"{key}={value}" for key, value in sbatch_args.items()],
                f"{self.WEBILASTIK_SOURCE_DIR}/scripts/launch_webilastik_worker__sbatch.sh",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
        except Exception as e:
            return e

        if process.returncode != 0:
            return Exception(stderr.decode())

        print(stdout.decode().split())
        job_id = SlurmJobId(int(stdout.decode().split()[3]))

        for i in range(5):
            await asyncio.sleep(0.7)
            print(f"~~~~~>> Trying to fetch job.... ({i})")
            job = await self.get_job_by_slurm_id(job_id=job_id)
            if isinstance(job, (Exception, SlurmJob)):
                return job
        return Exception(f"Could not retrieve job with id {job_id}")

    async def cancel(self, job: SlurmJob):
        process = await asyncio.create_subprocess_exec(
            "ssh", "-v", "-oBatchMode=yes", f"{self.user}@{self.hostname}",
            "--",
            "scancel", f"{job.job_id}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await process.communicate()
        if process.returncode != 0:
            return Exception(stderr.decode())
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
        starttime: "datetime | None" = None,
    ) -> "List[SlurmJob] | Exception":
        starttime_str = f"{starttime.year:04d}-{starttime.month:02d}-{starttime.day:02d}" if starttime else "2022-01-01"
        sacct_params = [
            "--json",
            f"--starttime={starttime_str}",
            "--endtime=now",
            f"--user={self.user}",
            f"--account={self.account}",
        ]

        if job_id is not None:
            sacct_params.append(f"--jobs={job_id}")
        if name is not None:
            sacct_params.append(f"--name={name}")
        if state != None and len(state) > 0:
            sacct_params.append(f"--state={','.join(s.value for s in state)}")

        process = await asyncio.create_subprocess_exec(
            "ssh", "-v", "-oBatchMode=yes", f"{self.user}@{self.hostname}",
            "--",
            "sacct", *sacct_params,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            return Exception(stderr.decode())
        payload = ensureJsonObject(json.loads(stdout))
        raw_jobs = ensureJsonArray(payload.get("jobs"))
        return [
            SlurmJob.from_json_value(raw_job)
            for raw_job in raw_jobs
            if SlurmJob.recognizes_raw_job(raw_job)
        ]

    async def get_usage_for_user(self, user_info: UserInfo) -> "NodeSeconds | Exception":
        this_month_jobs_result = await self.get_jobs(starttime=datetime.today().replace(day=1))
        if isinstance(this_month_jobs_result, Exception):
            return this_month_jobs_result
        node_seconds = sum(
            (job.duration * job.num_nodes)
            for job in this_month_jobs_result
            if job.duration != None and job.num_nodes != None and job.user_sub == user_info.sub
        )
        return NodeSeconds(node_seconds)

class JusufSshJobLauncher(SshJobLauncher):
    def __init__(self) -> None:
        super().__init__(
            user="vieira2",
            hostname="jusuf.fz-juelich.de",
            account="icei-hbp-2022-0010",
            WEBILASTIK_SOURCE_DIR=PurePosixPath("/p/project/icei-hbp-2022-0010/source/webilastik"),
            CONDA_ENV_DIR=PurePosixPath("/p/project/icei-hbp-2022-0010/miniconda3/envs/webilastik"),
            MODULES_TO_LOAD=["GCC/11.2.0", "OpenMPI/4.1.2"],
            extra_sbatch_opts={
                "--partition": "batch"
            },
            EXECUTOR_GETTER_IMPLEMENTATION="jusuf",
            CACHING_IMPLEMENTATION="redis_cache",
        )
