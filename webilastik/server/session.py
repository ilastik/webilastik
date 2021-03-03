from abc import ABC, abstractmethod
from pathlib import Path
import signal
from asyncio.subprocess import Process
import asyncio
import os
from typing import Type, TypeVar, Generic


SESSION_SCRIPT_PATH = Path(__file__).parent.joinpath("reverse_tunnel_to_master.sh")

SELF = TypeVar("SELF", bound="Session", covariant=True)

class Session(ABC):
    @classmethod
    @abstractmethod
    async def create(
        cls, #: Type[SELF],
        *,
        master_user: str,
        master_host: str,
        socket_at_session: Path,
        socket_at_master: Path,
        time_limit_seconds: int,
    ) -> "Session": # SELF:
        pass


class LocalSession(Session):
    @classmethod
    async def create(
        cls,
        *,
        master_user: str,
        master_host: str,
        socket_at_session: Path,
        socket_at_master: Path,
        time_limit_seconds: int,
    ) -> "LocalSession":
        process = await asyncio.create_subprocess_exec(
            str(SESSION_SCRIPT_PATH),
            env={
                **os.environ,
                "MASTER_USER": master_user,
                "MASTER_HOST": master_host,
                "SOCKET_PATH_AT_MASTER": str(socket_at_master),
                "SOCKET_PATH_AT_SESSION": str(socket_at_session),
            },
            preexec_fn=os.setsid
        )
        print(f"----->>>>>>>>>>>>>>> Started local session with pid={process.pid} and group {os.getpgid(process.pid)}")
        session = LocalSession(process=process, socket_at_master=socket_at_master)
        asyncio.create_task(session.kill(after_seconds=time_limit_seconds))
        return session

    # private. Use LocalSession.create instead
    def __init__(self, process: Process, socket_at_master: Path):
        self.process = process
        self.socket_at_master = socket_at_master

    async def kill(self, after_seconds: int):
        await asyncio.sleep(after_seconds)
        print(f"===>>>> gently killing local session (pid={self.process.pid})with SIGINT on group....")
        pgid = os.getpgid(self.process.pid)
        os.killpg(pgid, signal.SIGINT)
        # await asyncio.sleep(10)
        # print(f"===>>>> forcefully killing local session (pid={self.process.pid}) with SIGKILL on group....")
        # os.killpg(pgid, signal.SIGKILL)
        await self.process.wait()
        os.remove(self.socket_at_master)
