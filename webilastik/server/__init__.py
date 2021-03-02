import json
import os
from typing import Any, Dict
from subprocess import Popen
from pathlib import Path
import tempfile
import uuid
from urllib.parse import urljoin
import asyncio
from asyncio.subprocess import Process
import signal


import aiohttp


from aiohttp import web
from aiohttp.web_routedef import delete

from webilastik.ui.workflow.ws_pixel_classification_workflow import WsPixelClassificationWorkflow
import webilastik.ui.workflow.ws_pixel_classification_workflow as ws_workflow


SESSION_SCRIPT_PATH = str(Path(__file__).parent.joinpath("reverse_tunnel_to_master.sh"))

def start_pixel_classification_session(port: int):
    workflow = WsPixelClassificationWorkflow()
    workflow.run(port=port)

class LocalSession:
    @classmethod
    async def create(
        cls,
        *,
        master_username: str,
        master_host: str,
        socket_at_session: Path,
        socket_at_master: Path
    ):
        process = await asyncio.create_subprocess_exec(
            SESSION_SCRIPT_PATH,
            env={
                **os.environ,
                "MASTER_USER": master_username,
                "MASTER_HOST": master_host,
                "SOCKET_PATH_AT_MASTER": str(socket_at_master),
                "SOCKET_PATH_AT_SESSION": str(socket_at_session),
            },
            preexec_fn=os.setsid
        )
        print(f"----->>>>>>>>>>>>>>> Started local session with pid={process.pid} and group {os.getpgid(process.pid)}")
        return LocalSession(process=process, socket_at_master=socket_at_master)

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

class LocalSessionAllocator:
    def __init__(
        self,
        *,
        master_host: str,
        external_url: str,
        sockets_dir_at_master: Path,
        sockets_dir_at_session: Path,
        master_usermame: str,
    ):
        self.sockets_dir_at_master = sockets_dir_at_master
        self.sockets_dir_at_session = sockets_dir_at_session
        self.master_usermame = master_usermame
        self.master_host = master_host
        self.external_url = external_url

        self.sessions : Dict[uuid.UUID, LocalSession] = {}

        self.app = web.Application()
        self.app.add_routes([
            web.post('/session', self.spawn_session),
        ])

    def _make_session_url(self, session_id: uuid.UUID) -> str:
        return urljoin(self.external_url, f"session-{session_id}")

    async def spawn_session(self, request: web.Request):
        raw_payload = await request.content.read()
        payload_dict = json.loads(raw_payload.decode('utf8'))
        session_id = uuid.uuid4()

        asyncio.create_task(self.kill_session(session_id=session_id, after_seconds=payload_dict["session_duration"]))

        #FIXME: add to self.sessions?
        self.sessions[session_id] = await LocalSession.create(
            master_host=self.master_host,
            master_username=self.master_usermame,
            socket_at_session=self.sockets_dir_at_session.joinpath(f"{session_id}-to-master.sock"),
            socket_at_master=self.sockets_dir_at_master.joinpath(f"to-session-{session_id}.sock"),
        )

        return web.json_response(
            data={
                "session_url": self._make_session_url(session_id),
                "session_token": "FIXME", #use this to authenticate with the session server
            },
            headers={"Access-Control-Allow-Origin": "*"}
        )

    async def kill_session(self, session_id: uuid.UUID, after_seconds: int):
        await asyncio.sleep(after_seconds)
        await self.sessions.pop(session_id).kill()

    def run(self, port: int):
        web.run_app(self.app, port=port)

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--master-host")
    parser.add_argument("--external-url")
    parser.add_argument("--master-username", default="wwww-data")
    parser.add_argument("--sockets-dir-at-master", type=Path, default=Path(tempfile.gettempdir()))
    parser.add_argument("--sockets-dir-at-session", type=Path, default=Path(tempfile.gettempdir()))

    args = parser.parse_args()

    # multiprocessing.set_start_method('spawn') #start a fresh interpreter so it doesn't 'inherit' the event loop
    LocalSessionAllocator(
        master_host=args.master_host,
        external_url=args.external_url,
        master_usermame=args.master_username,
        sockets_dir_at_master=args.sockets_dir_at_master,
        sockets_dir_at_session=args.sockets_dir_at_session,
    ).run(port=5000)
