#pyright: strict

import asyncio
from enum import Enum
from typing import ClassVar, NewType, Dict, Mapping, List, Sequence
import uuid
from pathlib import PurePosixPath
import json

from ndstructs.utils.json_serializable import JsonValue, ensureJsonArray, ensureJsonInt, ensureJsonObject, ensureJsonString

from webilastik.libebrains.user_info import UserInfo
from webilastik.libebrains.user_token import UserToken

class JobState(Enum):
    PENDING="PENDING"
    RUNNING="RUNNING"
    COMPLETED="COMPLETED"
    CANCELLED="CANCELLED"
    FAILED="FAILED"
    TIMEOUT="TIMEOUT"

    def is_done(self) -> bool:
        return self in (JobState.COMPLETED, JobState.CANCELLED, JobState.FAILED, JobState.TIMEOUT)

    def to_json_value(self) -> str:
        return self.value

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "JobState":
        value_str = ensureJsonString(value)
        for state in JobState:
            if state.value == value_str:
                return state
        raise ValueError(f"Bad job state: {value_str}")


Minutes = NewType("Minutes", int)
Seconds = NewType("Seconds", int)
SlurmJobId = NewType("SlurmJobId", int)


class SlurmJob:
    NAME_PREFIX: ClassVar[str] = "EBRAINS"

    def __init__(
        self,
        *,
        job_id: SlurmJobId,
        name: str,
        state: JobState,
        duration: "Seconds | None",
    ) -> None:
        self.job_id = job_id
        self.state = state
        self.duration = duration
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

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "SlurmJob":
        value_obj = ensureJsonObject(value)
        raw_state = ensureJsonObject(value_obj.get("state"))
        state = JobState.from_json_value(raw_state.get("current"))

        if state.is_done():
            time_obj = ensureJsonObject(value_obj["time"])
            start = ensureJsonInt(time_obj["start"])
            end = ensureJsonInt(time_obj["end"])
            duration = Seconds(end - start)
        else:
            duration = None

        return SlurmJob(
            job_id=SlurmJobId(ensureJsonInt(value_obj.get("job_id"))),
            name=ensureJsonString(value_obj.get("name")),
            state=state,
            duration=duration,
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

        extra_sbatch_opts: Mapping[str, str] = {},
        extra_environment_vars: Mapping[str, str] = {}
    ) -> None:
        self.user = user
        self.hostname = hostname
        self.account = account

        self.WEBILASTIK_SOURCE_DIR = WEBILASTIK_SOURCE_DIR
        self.CONDA_ENV_DIR = CONDA_ENV_DIR
        self.MODULES_TO_LOAD = MODULES_TO_LOAD

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
                "ssh", "-v", f"{self.user}@{self.hostname}",
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
            await asyncio.sleep(0.5)
            print(f"~~~~~>> Trying to fetch job.... ({i})")
            job = await self.get_job(job_id=job_id)
            if isinstance(job, (Exception, SlurmJob)):
                return job
        return Exception(f"Could not retrieve job with id {job_id}")

    async def cancel(self, job: SlurmJob):
        process = await asyncio.create_subprocess_exec(
            "ssh", "-v", f"{self.user}@{self.hostname}",
            "--",
            "scancel", f"{job.job_id}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await process.communicate()
        if process.returncode != 0:
            return Exception(stderr.decode())
        return None

    async def get_job(self, job_id: SlurmJobId) -> "SlurmJob | None | Exception":
        jobs_result = await self.get_jobs(job_id=job_id)
        if isinstance(jobs_result, Exception):
            return jobs_result
        if len(jobs_result) == 0:
            return None
        return jobs_result[0]

    async def get_jobs(self, job_id: "SlurmJobId | None" = None) -> "List[SlurmJob] | Exception":
        sacct_params = [
            "--json",
            "--starttime=2022-01-01",
            f"--user={self.user}",
            f"--account={self.account}",
        ]

        if job_id is not None:
            sacct_params.append(f"--jobs={job_id}")

        process = await asyncio.create_subprocess_exec(
            "ssh", "-v", f"{self.user}@{self.hostname}",
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
        )
