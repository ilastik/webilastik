from pathlib import Path
from typing import Type
import asyncio
from asyncio.subprocess import Process
import os
import signal


from webilastik.hpc.job import HpcEnvironment, JobDescription, JobImport

class HpcSession:
    @classmethod
    async def create(
        cls: Type["HpcSession"],
        *,
        master_username: str,
        master_host: str,
        socket_at_session: Path,
        socket_at_master: Path
    ) -> "HpcSession":
        process = await asyncio.create_subprocess_exec(
            __file__,
            "--master-user=" + master_username,
            "--master-host=" + master_host,
            "--socket-at-session=" + str(socket_at_master),
            "--socket-at-master=" + str(socket_at_session),
            preexec_fn=os.setsid
        )
        print(f"----->>>>>>>>>>>>>>> Started local session with pid={process.pid} and group {os.getpgid(process.pid)}")
        return HpcSession(process=process, socket_at_master=socket_at_master)

    # private. Use LocalSession.create instead
    def __init__(self, process: Process, socket_at_master: Path):
        self.process = process
        self.socket_at_master = socket_at_master

    async def kill(self):
        print(f"===>>>> gently killing local session (pid={self.process.pid})with SIGINT on group....")
        pgid = os.getpgid(self.process.pid)
        os.killpg(pgid, signal.SIGINT)
        # await asyncio.sleep(10)
        # print(f"===>>>> forcefully killing local session (pid={self.process.pid}) with SIGKILL on group....")
        # os.killpg(pgid, signal.SIGKILL)
        await self.process.wait()
        os.remove(self.socket_at_master)


if __name__ == '__main__':
    import tempfile
    from argparse import ArgumentParser

    from webilastik.server.session import SESSION_SCRIPT_PATH

    parser = ArgumentParser()
    parser.add_argument("--master-host")
    parser.add_argument("--external-url")
    parser.add_argument("--master-username", default="wwww-data")
    parser.add_argument("--socket-at-session", type=Path)
    parser.add_argument("--sockets-at-master", type=Path)

    parser.add_argument("--hpc-project-name")
    parser.add_argument("--hpc-python-executable", type=Path)
    parser.add_argument("--hpc-webilastik-dir", type=Path)

    args = parser.parse_args()

    job_desc = JobDescription(
        Executable=f"{args.hpc_webilastik_dir}/webilastik/server/reverse_tunnel_to_master.sh",
        Environment={
            "MASTER_USER": args.master_username,
            "MASTER_HOST": args.master_host,
            "SOCKET_PATH_AT_MASTER": str(args.socket_at_session),
            "SOCKET_PATH_AT_SESSION": str(args.socket_at_master),
            "PYTHON_EXECUTABLE": args.hpc_python_executable
        },
        Project=args.hpc_project_name,
    )

    hpc_env = HpcEnvironment.from_environ()
    hpc_env.run_job(job_desc)
