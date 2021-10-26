from functools import wraps
import json
from typing import Any, Callable, Coroutine, Dict, NoReturn, TypeVar,  Type, Generic, Optional
from pathlib import Path, PurePosixPath
import tempfile
import uuid
import asyncio
import sys

import aiohttp

from webilastik.libebrains.user_token import UserToken
from webilastik.libebrains.oidc_client import OidcClient
from aiohttp import web
import os
import logging

from webilastik.utility.url import Url, Protocol
from webilastik.server.session import Session, LocalSession

# logging.basicConfig(level=logging.DEBUG)

SESSION_TYPE = TypeVar("SESSION_TYPE", bound=Session)

def get_requested_url(request: web.Request) -> Url:
    protocol = Protocol.from_str(request.headers['X-Forwarded-Proto'])
    host = request.headers['X-Forwarded-Host']
    if ":" in host:
        hostname, port_str = host.split(":")
        port = int(port_str)
    else:
        hostname = host
        port = None
    path = PurePosixPath(request.headers['X-Forwarded-Prefix']) / request.url.path.lstrip("/")
    url = Url(protocol=protocol, hostname=hostname, port=port, path=path)
    return  url

def redirect_to_ebrains_login(request: web.Request, oidc_client: OidcClient) -> NoReturn:
    raise web.HTTPFound(location=oidc_client.create_user_login_url(
        redirect_uri=get_requested_url(request),
    ).raw)

class EbrainsSession:
    AUTH_COOKIE_KEY = "ebrains_access_token"

    def __init__(self, user_token: UserToken):
        self.user_token = user_token

    @classmethod
    def from_cookie(cls, request: web.Request) -> Optional["EbrainsSession"]:
        access_token = request.cookies.get(cls.AUTH_COOKIE_KEY)
        if access_token is None:
            return None
        user_token = UserToken(access_token=access_token)
        if not user_token.is_valid():
            return None
        return EbrainsSession(user_token=user_token)

    @classmethod
    def from_code(cls, request: web.Request, oidc_client: OidcClient) -> Optional["EbrainsSession"]:
        auth_code = request.query.get("code")
        if auth_code is None:
            return None
        user_token = oidc_client.get_user_token(code=auth_code, redirect_uri=get_requested_url(request))
        return EbrainsSession(user_token=user_token)

    @classmethod
    def try_from_request(cls, request: web.Request, oidc_client: OidcClient) -> Optional["EbrainsSession"]:
        return cls.from_cookie(request) or EbrainsSession.from_code(request, oidc_client=oidc_client)

    def set_cookie(self, response: web.Response) -> web.Response:
        response.set_cookie(
            name=self.AUTH_COOKIE_KEY, value=self.user_token.access_token, secure=True
        )
        return response


def require_ebrains_login(
    endpoint: Callable[["SessionAllocator[SESSION_TYPE]", web.Request], Coroutine[Any, Any, web.Response]]
) -> Callable[["SessionAllocator[SESSION_TYPE]", web.Request], Coroutine[Any, Any, web.Response]]:

    @wraps(endpoint)
    async def wrapper(self: "SessionAllocator[SESSION_TYPE]", request: web.Request) -> web.Response:
        if self.oidc_client is None:
            return await endpoint(self, request)
        ebrains_session = EbrainsSession.try_from_request(request, oidc_client=self.oidc_client)
        if ebrains_session is None:
            redirect_to_ebrains_login(request, oidc_client=self.oidc_client)
        response = await endpoint(self, request)
        return ebrains_session.set_cookie(response)

    return wrapper


class SessionAllocator(Generic[SESSION_TYPE]):
    def __init__(
        self,
        *,
        session_type: Type[SESSION_TYPE],
        master_host: str,
        external_url: Url,
        sockets_dir_at_master: Path,
        master_username: str,
        oidc_client: OidcClient,
    ):
        self.session_type = session_type
        self.sockets_dir_at_master = sockets_dir_at_master
        self.master_username = master_username
        self.master_host = master_host
        self.external_url = external_url
        self.oidc_client = oidc_client

        self.sessions : Dict[uuid.UUID, Session] = {}

        self.app = web.Application()
        self.app.add_routes([
            web.get('/check_login', self.check_login),
            web.get('/login_then_close', self.login_then_close),
            web.get('/hello', self.hello),
            web.post('/session', self.spawn_session),
            web.get('/session/{session_id}', self.session_status),
            web.static('/', Path(__file__) / "../../../public", follow_symlinks=True, show_index=True),
        ])

    def _make_session_url(self, session_id: uuid.UUID) -> Url:
        return self.external_url.joinpath(f"session-{session_id}")

    def _make_socket_path_at_master(self, session_id: uuid.UUID) -> Path:
        return self.sockets_dir_at_master.joinpath(f"to-session-{session_id}")

    @require_ebrains_login
    async def hello(self, request: web.Request) -> web.Response:
        return web.json_response("hello!", status=200)

    async def check_login(self, request: web.Request) -> web.Response:
        if EbrainsSession.from_cookie(request) is None:
            return web.json_response({"logged_in": False}, status=401)
        return web.json_response({"logged_in": True}, status=200)

    @require_ebrains_login
    async def login_then_close(self, request: web.Request) -> web.Response:
        return  web.Response(
            text="""
                <html>
                    <head>
                        <meta charset="UTF-8">
                        <script>window.close()</script>
                    </head>>
                    <body>
                        <p>You've logged into ebrains. You can close this tab now</p>
                    </body>
                </html>
            """,
            content_type='text/html'
        )

    @require_ebrains_login
    async def spawn_session(self, request: web.Request) -> web.Response:
        raw_payload = await request.content.read()
        try:
            payload_dict = json.loads(raw_payload.decode('utf8'))
            session_duration = int(payload_dict["session_duration"])
        except Exception:
            return web.json_response({"error": "Bad payload"}, status=400)
        session_id = uuid.uuid4()

        ebrains_session = EbrainsSession.try_from_request(request, oidc_client=self.oidc_client)
        if ebrains_session is None:
            redirect_to_ebrains_login(request, self.oidc_client)

        #FIXME: remove stuff from self.sessions
        self.sessions[session_id] = await self.session_type.create(
            session_id=session_id,
            master_host=self.master_host,
            master_username=self.master_username,
            socket_at_master=self._make_socket_path_at_master(session_id),
            time_limit_seconds=session_duration,
            ebrains_user_token=ebrains_session.user_token
        )

        return web.json_response(
            {
                "id": str(session_id),
                "url": self._make_session_url(session_id).raw,
            },
        )

    @require_ebrains_login
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
    parser.add_argument("--session-type", choices=["Local", "Hpc"], required=True)
    parser.add_argument("--master-host", required=True, help="Host name or IP where workers should ssh back to")
    parser.add_argument("--master-username", default="wwww-data", help="username with which workers should ssh back to master")
    parser.add_argument("--external-url", type=Url.parse, required=True, help="Url from which sessions can be accessed (where the session sockets live)")
    parser.add_argument("--sockets-dir-at-master", type=Path, default=Path(tempfile.gettempdir()))
    parser.add_argument(
        "--oidc-client-json",
        help="Path to a json file representing the keycloak client or the special value 'skip'. You can get this data via OidcClient.get"
    )


    args = parser.parse_args()

    # multiprocessing.set_start_method('spawn') #start a fresh interpreter so it doesn't 'inherit' the event loop
    if args.session_type == "Local":
        session_type = LocalSession
    else:
        from webilastik.server.hpc_session import HpcSession
        session_type = HpcSession

    # if args.oidc_client_json == "skip":
    #     oidc_client = None
    # else:
    #     with open(args.oidc_client_json) as f:
    #         oidc_client = OidcClient.from_json_value(json.load(f))

    with open(args.oidc_client_json) as f:
        oidc_client = OidcClient.from_json_value(json.load(f))

    SessionAllocator(
        session_type=session_type,
        master_host=args.master_host,
        external_url=args.external_url,
        master_username=args.master_username,
        sockets_dir_at_master=args.sockets_dir_at_master,
        oidc_client=oidc_client,
    ).run(port=5000)
