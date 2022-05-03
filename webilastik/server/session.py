# pyright: reportUnusedCallResult=false

from abc import ABC, abstractmethod
from pathlib import Path
import signal
from asyncio.subprocess import Process
import asyncio
import os
from typing import Type, TypeVar, Generic
import uuid
from uuid import UUID
import sys

from webilastik.libebrains.user_token import UserToken
import webilastik.ui.workflow.ws_pixel_classification_workflow

SESSION_SCRIPT_PATH = Path(__file__).parent.joinpath("reverse_tunnel_to_master.sh")

SELF = TypeVar("SELF", bound="Session", covariant=True)

class Session(ABC):
    @classmethod
    @abstractmethod
    async def create(
        cls, #: Type[SELF],
        *,
        session_id: UUID,
        master_username: str,
        master_host: str,
        socket_at_master: Path,
        time_limit_seconds: int,
        user_token: UserToken,
    ) -> "Session": # SELF:
        pass

    async def kill(self, after_seconds: int):
        pass

    @abstractmethod
    def get_id(self) -> UUID:
        ...

class LocalSession(Session):
    @classmethod
    async def create(
        cls,
        *,
        session_id: UUID,
        master_username: str,
        master_host: str,
        socket_at_master: Path,
        time_limit_seconds: int,
        user_token: UserToken,
    ) -> "LocalSession":
        local_socket = Path(f"/tmp/{session_id}-to-master")
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            webilastik.ui.workflow.ws_pixel_classification_workflow.__file__,
            f"--ebrains-user-access-token={user_token.access_token}",
            f"--listen-socket={local_socket}",
            "tunnel",
            f"--remote-username={master_username}",
            f"--remote-host={master_host}",
            f"--remote-unix-socket={str(socket_at_master)}",
            preexec_fn=os.setsid
        )
        print(f"----->>>>>>>>>>>>>>> Started local session with pid={process.pid} and group {os.getpgid(process.pid)}")
        session = LocalSession(
            session_id=session_id,
            process=process,
            local_socket=local_socket,
            socket_at_master=socket_at_master,
            master_username=master_username,
            master_host=master_host
        )
        asyncio.create_task(session.kill(after_seconds=time_limit_seconds))
        return session

    # private. Use LocalSession.create instead
    def __init__(
        self,
        *,
        session_id: UUID,
        process: Process,
        local_socket: Path,
        socket_at_master: Path,
        master_username: str,
        master_host: str
    ):
        self.session_id = session_id
        self.process = process
        self.local_socket = local_socket
        self.socket_at_master = socket_at_master
        self.master_username = master_username
        self.master_host = master_host
        super().__init__()

    def get_id(self) -> UUID:
        return self.session_id

    async def kill(self, after_seconds: int):
        await asyncio.sleep(after_seconds)
        try:
            pgid = os.getpgid(self.process.pid)
            print(f"===>>>> AUTOKILL: gently killing local session (pid={self.process.pid}) with SIGINT on group....")
            os.killpg(pgid, signal.SIGINT)
            await asyncio.sleep(10)
            print(f"===>>>> AUTOKILL: Killing local session (pid={self.process.pid}) with SIGKILL on group....")
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            print(f"AUTOKILL: Could not find process {self.process.pid}")

        await self.process.wait()

        try:
            os.remove(self.socket_at_master)
        except FileNotFoundError:
            pass

        try:
            os.remove(self.local_socket)
        except FileNotFoundError:
            pass
