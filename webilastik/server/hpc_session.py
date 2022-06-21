#!/usr/bin/env python3
# pyright: reportUnusedCallResult=false


from pathlib import Path
from typing import Type
import asyncio
from asyncio.subprocess import Process
import os
import signal
import tempfile
from argparse import ArgumentParser
from uuid import UUID
from webilastik.libebrains.user_token import UserToken

from webilastik.server.session import Session, SESSION_SCRIPT_PATH
from webilastik.hpc.job import EBrainsClient, JobDescription, JobImport, JobResources


HPC_PROJECT_NAME = os.environ["HPC_PROJECT_NAME"]
HPC_PYTHON_EXECUTABLE = os.environ["HPC_PYTHON_EXECUTABLE"]
HPC_WEBILASTIK_DIR = os.environ["HPC_WEBILASTIK_DIR"]
EBRAINS_REFRESH_TOKEN = os.environ["EBRAINS_REFRESH_TOKEN"]
EBRAINS_APP_ID = os.environ["EBRAINS_APP_ID"]
EBRAINS_APP_SECRET = os.environ["EBRAINS_APP_SECRET"]


class HpcSession(Session):
    @classmethod
    async def create(
        cls: Type["HpcSession"],
        *,
        session_id: UUID,
        master_username: str,
        master_host: str,
        socket_at_master: Path,
        time_limit_seconds: int,
        user_token: UserToken,
    ) -> "HpcSession":
        process = await asyncio.create_subprocess_exec(
            __file__,
            "--ebrains-user-access-token=" + user_token.access_token,
            "--master-username=" + master_username,
            "--master-host=" + master_host,
            "--socket-at-master=" + str(socket_at_master),

            "--resources-time-limit-seconds=" + str(time_limit_seconds),
            preexec_fn=os.setsid,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return_code = process.returncode
        if return_code != 0:
            raise RuntimeError(f"Scheduling HpcSession failed with code {return_code}\nstdout:\n{stdout}\n\n\nstderr:\n{stderr}")
        try:
            job_id = UUID(stdout.decode('utf8').strip())
            print(f"New session created: {job_id}")
        except Exception:
            raise RuntimeError(f"Could not grab uuid: Scheduling HpcSession failed with code {return_code}\nstdout:\n{stdout}\n\n\nstderr:\n{stderr}")

        print(f"Created job {job_id} for session {session_id}")
        return HpcSession(session_id=session_id, job_id=job_id)

    # private. Use LocalSession.create instead
    def __init__(self, session_id: UUID, job_id: UUID):
        self.session_id = session_id
        self.job_id = job_id
        super().__init__()

    def get_id(self) -> UUID:
        return self.session_id

    async def kill(self, after_seconds: int):
        ... #FIXME: implement early killing

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--ebrains-user-access-token", type=str, required=True)
    parser.add_argument("--master-host")
    parser.add_argument("--master-username", default="wwww-data")
    parser.add_argument("--socket-at-session", type=Path)
    parser.add_argument("--socket-at-master", type=Path)

    parser.add_argument("--resources-time-limit-seconds", type=int, default=10 * 60)

    args = parser.parse_args()

    job_desc = JobDescription(
        Executable="srun",
        Arguments=[
            HPC_PYTHON_EXECUTABLE,
            "-u",
            f"{HPC_WEBILASTIK_DIR}/webilastik/ui/workflow/ws_pixel_classification_workflow.py",
            f"--ebrains-user-access-token={args.ebrains_user_access_token}",
            f"--listen-socket=to-master",
            "tunnel",
            f"--remote-username={args.master_username}",
            f"--remote-host={args.master_host}",
            f"--remote-unix-socket={str(args.socket_at_master)}",
        ],
        Project=HPC_PROJECT_NAME,
        Resources=JobResources(
            Nodes=1,
            # CPUs=2,
            Runtime=args.resources_time_limit_seconds
        )
    )
    ebrains_env = EBrainsClient(
        ebrains_refresh_token=EBRAINS_REFRESH_TOKEN,
        ebrains_app_id=EBRAINS_APP_ID,
        ebrains_app_secret=EBRAINS_APP_SECRET,
    )
    job = ebrains_env.run_job(job_desc)
    print(job.job_id)
