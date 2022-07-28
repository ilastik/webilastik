#pyright: strict

import asyncio
from collections.abc import Sequence
from typing import NewType, Dict, Mapping
import uuid
from pathlib import PurePosixPath

from webilastik.libebrains.user_token import UserToken

class SlurmJob:
    def __init__(self, slurm_job_id: int, webilastik_session_id: uuid.UUID) -> None:
        self.slurm_job_id = slurm_job_id
        self.webilastik_session_id = webilastik_session_id
        super().__init__()

Minutes = NewType("Minutes", int)

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
        time: Minutes,
        EBRAINS_USER_ACCESS_TOKEN: UserToken,
        WORKER_SESSION_ID: uuid.UUID,
    ) -> "SlurmJob | Exception":
        env_vars: Dict[str, str] = {
            "WEBILASTIK_SOURCE_DIR": str(self.WEBILASTIK_SOURCE_DIR),
            "CONDA_ENV_DIR": str(self.CONDA_ENV_DIR),
            "WORKER_SESSION_ID": str(WORKER_SESSION_ID),
            "MODULES_TO_LOAD": '@'.join(self.MODULES_TO_LOAD),
            "EBRAINS_USER_ACCESS_TOKEN": EBRAINS_USER_ACCESS_TOKEN.access_token,
            **self.extra_environment_vars
        }

        sbatch_args: Dict[str, str] = {
            "--job-name": f"session-{WORKER_SESSION_ID}",
            "--nodes": "1",
            "--ntasks": "2",
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
        if process.returncode == 0:
            print(f"Success!!!")
            print(stdout.decode().split())
            slurm_job_id = int(stdout.decode().split()[3])
            return SlurmJob(
                slurm_job_id=slurm_job_id,
                webilastik_session_id=WORKER_SESSION_ID
            )
        else:
            return Exception(stderr.decode())

    async def cancel(self, job: SlurmJob):
        process = await asyncio.create_subprocess_exec(
            "ssh", "-v", f"{self.user}@{self.hostname}",
            "--",
            "scancel", f"--account={self.account}", f"{job.slurm_job_id}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await process.communicate()
        if process.returncode == 0:
            return None
        else:
            return Exception(stderr.decode())

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
