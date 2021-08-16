import json
from typing import Any, Dict, TypeVar,  Type, Generic
from pathlib import Path
import tempfile
import uuid
from urllib.parse import urljoin
import asyncio
from aiohttp import web
import os
import logging
logging.basicConfig(level=logging.DEBUG)

from aiohttp.web_routedef import head

import jwt
from webilastik.utility.url import Url, Protocol
from webilastik.server.session import Session, LocalSession

logging.basicConfig(level=logging.DEBUG)

SESSION_TYPE = TypeVar("SESSION_TYPE", bound=Session)

SESSION_SECRET = os.environ["SESSION_SECRET"]

class SessionAllocator(Generic[SESSION_TYPE]):
    def __init__(
        self,
        *,
        session_type: Type[SESSION_TYPE],
        master_host: str,
        external_url: Url,
        sockets_dir_at_master: Path,
        master_username: str,
    ):
        self.session_type = session_type
        self.sockets_dir_at_master = sockets_dir_at_master
        self.master_username = master_username
        self.master_host = master_host
        self.external_url = external_url

        self.sessions : Dict[uuid.UUID, Session] = {}

        self.app = web.Application()
        self.app.add_routes([
            web.post('/session', self.spawn_session),
            web.get('/session/{session_id}', self.session_status),
            web.static('/', Path(__file__) / "../../../overlay/public", follow_symlinks=True, show_index=True),
        ])

    def _make_session_url(self, session_id: uuid.UUID) -> Url:
        return self.external_url.joinpath(f"session-{session_id}")

    def _make_socket_path_at_master(self, session_id: uuid.UUID) -> Path:
        return self.sockets_dir_at_master.joinpath(f"to-session-{session_id}")

    async def spawn_session(self, request: web.Request):
        raw_payload = await request.content.read()
        try:
            payload_dict = json.loads(raw_payload.decode('utf8'))
            session_duration = int(payload_dict["session_duration"])
        except Exception:
            return web.json_response({"error": "Bad payload"}, status=400)
        session_id = uuid.uuid4()

        #FIXME: remove stuff from self.sessions
        self.sessions[session_id] = await self.session_type.create(
            session_id=session_id,
            master_host=self.master_host,
            master_username=self.master_username,
            socket_at_master=self._make_socket_path_at_master(session_id),
            time_limit_seconds=session_duration
        )

        return web.json_response(
            {
                "id": str(session_id),
                "url": self._make_session_url(session_id).raw,
                "token": jwt.encode(
                    {"sid": str(session_id)},
                    SESSION_SECRET,
                    algorithm="HS256"
                )
            },
        )

    async def session_status(self, request: web.Request):
        # FIXME: do security checks here?
        try:
            session_id =  uuid.UUID(request.match_info.get("session_id"))
        except Exception:
            return web.json_response({"error": "Bad session id"}, status=400)
        if session_id not in self.sessions:
            return web.json_response({"error": "Session not found"}, status=404)
        return web.json_response(
            {
                "status": "ready" if self._make_socket_path_at_master(session_id).exists() else "not ready",
                "url": self._make_session_url(session_id).raw
            },
        )

    async def kill_session(self, session_id: uuid.UUID, after_seconds: int = 0):
        await asyncio.sleep(after_seconds)
        await self.sessions.pop(session_id).kill(after_seconds=after_seconds)

    def run(self, port: int):
        web.run_app(self.app, port=port)

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--session-type", choices=["Local", "Hpc"])
    parser.add_argument("--master-host")
    parser.add_argument("--external-url")
    parser.add_argument("--master-username", default="wwww-data")
    parser.add_argument("--sockets-dir-at-master", type=Path, default=Path(tempfile.gettempdir()))

    args = parser.parse_args()

    # multiprocessing.set_start_method('spawn') #start a fresh interpreter so it doesn't 'inherit' the event loop
    if args.session_type == "Local":
        session_type = LocalSession
    else:
        from webilastik.server.hpc_session import HpcSession
        session_type = HpcSession
    SessionAllocator(
        session_type=session_type,
        master_host=args.master_host,
        external_url=args.external_url,
        master_username=args.master_username,
        sockets_dir_at_master=args.sockets_dir_at_master,
    ).run(port=5000)
