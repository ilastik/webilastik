# pyright: strict
# pyright: reportUnusedCallResult=false

from functools import wraps
import json
from typing import Any, Callable, Coroutine, Dict, List, Literal, NoReturn, Optional, Set
from pathlib import Path, PurePosixPath
import uuid
import asyncio
import sys
from datetime import datetime

from aiohttp import web
import aiohttp
from aiohttp.client import ClientSession
from cryptography.fernet import Fernet
from ndstructs.utils.json_serializable import JsonValue

from webilastik.libebrains.compute_session_launcher import CscsSshJobLauncher, JusufSshJobLauncher, LocalJobLauncher, Minutes, ComputeSession, SshJobLauncher
from webilastik.libebrains.user_token import UserToken
from webilastik.libebrains.oidc_client import OidcClient, Scope
from webilastik.server.rpc.dto import (
    CheckLoginResultDto,
    CloseComputeSessionParamsDto,
    CloseComputeSessionResponseDto,
    ComputeSessionStatusDto,
    CreateComputeSessionParamsDto,
    GetAvailableHpcSitesResponseDto,
    GetComputeSessionStatusParamsDto,
    ListComputeSessionsParamsDto,
    ListComputeSessionsResponseDto,
    MessageParsingError,
    RpcErrorDto,
)
from webilastik.config import SessionAllocatorConfig
from webilastik.utility import ComputeNodes, Hostname, NodeHours, Username
from webilastik.utility.url import Url


def get_requested_url(request: web.Request) -> Url:
    protocol = request.headers['X-Forwarded-Proto'].lower()
    assert protocol == "http" or protocol == "https"
    host = request.headers['X-Forwarded-Host']
    if ":" in host:
        hostname, port_str = host.split(":")
        port = int(port_str)
    else:
        hostname = host
        port = None
    path = PurePosixPath(request.get('X-Forwarded-Prefix', "/")) / request.url.path.lstrip("/")
    url = Url(protocol=protocol, hostname=hostname, port=port, path=path)
    return  url

def redirect_to_ebrains_login(request: web.Request, oidc_client: OidcClient) -> NoReturn:
    raise web.HTTPFound(
        location=oidc_client.create_user_login_url(
            redirect_uri=get_requested_url(request),
            scopes=set([Scope.OPENID, Scope.GROUP, Scope.TEAM, Scope.EMAIL, Scope.PROFILE]),
        ).raw
    )

def uncachable_json_response(payload: JsonValue, *, status: int) -> web.Response:
    return web.json_response(
        payload,
        status=status,
        headers={
            "Cache-Control": "no-store, must-revalidate",
            "Expires": "0",
        }
    )

class EbrainsLogin:
    EBRAINS_USER_ACCESS_TOKEN_COOKIE_KEY="ebrains_user_access_token"
    EBRAINS_USER_REFRESH_TOKEN_COOKIE_KEY="ebrains_user_refresh_token"

    def __init__(self, user_token: UserToken, refreshed: bool):
        self.user_token = user_token
        self.refreshed = refreshed
        super().__init__()

    @classmethod
    async def from_cookie(cls, request: web.Request, http_client_session: ClientSession, oidc_client: OidcClient) -> Optional["EbrainsLogin"]:
        access_token = request.cookies.get(cls.EBRAINS_USER_ACCESS_TOKEN_COOKIE_KEY)
        refresh_token = request.cookies.get(cls.EBRAINS_USER_REFRESH_TOKEN_COOKIE_KEY)
        if access_token is None or refresh_token is None:
            return None
        user_token = UserToken(access_token=access_token, refresh_token=refresh_token)
        if await user_token.is_valid(http_client_session):
            return EbrainsLogin(user_token=user_token, refreshed=False)
        refreshed_token = await user_token.async_refreshed(http_client_session=http_client_session, oidc_client=oidc_client)
        if isinstance(refreshed_token, Exception):
            return None
        return EbrainsLogin(user_token=refreshed_token, refreshed=True)

    @classmethod
    async def from_code(cls, request: web.Request, oidc_client: OidcClient, http_client_session: ClientSession) -> Optional["EbrainsLogin"]:
        auth_code = request.query.get("code")
        if auth_code is None:
            return None
        user_token = await UserToken.async_from_code(
            code=auth_code, redirect_uri=get_requested_url(request), http_client_session=http_client_session, oidc_client=oidc_client
        )
        return EbrainsLogin(user_token=user_token, refreshed=True)

    def set_cookie(self, response: web.Response) -> web.Response:
        response.set_cookie(
            name=self.EBRAINS_USER_ACCESS_TOKEN_COOKIE_KEY, value=self.user_token.access_token, secure=True
        )
        response.set_cookie(
            name=self.EBRAINS_USER_REFRESH_TOKEN_COOKIE_KEY, value=self.user_token.refresh_token, secure=True
        )
        return response


def require_ebrains_login(
    endpoint: Callable[["SessionAllocator", EbrainsLogin, web.Request], Coroutine[Any, Any, web.Response]]
) -> Callable[["SessionAllocator", web.Request], Coroutine[Any, Any, web.Response]]:

    @wraps(endpoint)
    async def wrapper(self: "SessionAllocator", request: web.Request) -> web.Response:
        ebrains_login = await EbrainsLogin.from_cookie(request, http_client_session=self.http_client_session, oidc_client=self.oidc_client)
        if ebrains_login is None:
            ebrains_login = await EbrainsLogin.from_code(request, oidc_client=self.oidc_client, http_client_session=self.http_client_session)
        if ebrains_login is None:
            redirect_to_ebrains_login(request, oidc_client=self.oidc_client)
        response = await endpoint(self, ebrains_login, request)
        if ebrains_login.refreshed:
            ebrains_login.set_cookie(response)
        return response

    return wrapper

HpcSiteName = Literal["LOCAL_DASK", "LOCAL_PROCESS_POOL", "CSCS", "JUSUF"]
HPC_SITE_NAMES: Set[HpcSiteName] = set(["LOCAL_DASK", "LOCAL_PROCESS_POOL", "CSCS", "JUSUF"])

class SessionAllocator:
    def __init__(
        self,
        *,
        fernet: Fernet,
        external_url: Url,
        oidc_client: OidcClient,
        allow_local_sessions: bool = False,
    ):
        self.fernet = fernet
        self.session_launchers: Dict[HpcSiteName, SshJobLauncher] = {}
        if allow_local_sessions:
            self.session_launchers["LOCAL_DASK"] = LocalJobLauncher(fernet=fernet, executor_getter="dask")
            self.session_launchers["LOCAL_PROCESS_POOL"] = LocalJobLauncher(fernet=fernet, executor_getter="default")
        self.session_launchers.update({
            "JUSUF": JusufSshJobLauncher(fernet=fernet),
            "CSCS": CscsSshJobLauncher(fernet=fernet),
        })
        self.external_url: Url = external_url
        self.oidc_client: OidcClient = oidc_client
        self._http_client_session: Optional[ClientSession] = None

        self.quotas_lock = asyncio.Lock()
        self.session_user_locks: Dict[uuid.UUID, asyncio.Lock] = {}

        self.app = web.Application()
        self.app.add_routes([
            web.get('/', self.welcome),
            web.get('/api/viewer', self.login_then_open_viewer), #FIXME: this is only here because the oidc redirect URLs must start with /api
            web.get('/api/check_login', self.check_login),
            web.get('/api/login_then_close', self.login_then_close),
            web.get('/api/hello', self.hello),
            web.post('/api/create_compute_session', self.create_compute_session),
            web.post('/api/list_sessions', self.list_sessions),
            web.post('/api/get_available_hpc_sites', self.get_available_hpc_sites),
            web.post('/api/get_session_status', self.get_session_status),
            web.post('/api/close_session', self.close_session),
            web.post('/api/get_ebrains_token', self.get_ebrains_token), #FIXME: I'm using this in NG web workers
            web.get('/service_worker.js', self.serve_service_worker),
        ])
        super().__init__()

    @property
    def http_client_session(self) -> ClientSession:
        if self._http_client_session is None:
            self._http_client_session = aiohttp.ClientSession()
        return self._http_client_session

    async def get_ebrains_token(self, request: web.Request) -> web.Response:
        origin = request.headers.get("Origin")
        if origin != "https://app.ilastik.org":
            return uncachable_json_response(RpcErrorDto(error=f"Bad origin: {origin}").to_json_value(), status=400)
        ebrains_login = await EbrainsLogin.from_cookie(request, http_client_session=self.http_client_session, oidc_client=self.oidc_client)
        if ebrains_login is None:
            return uncachable_json_response(RpcErrorDto(error=f"Not logged in").to_json_value(), status=400)
        response = web.json_response({EbrainsLogin.EBRAINS_USER_ACCESS_TOKEN_COOKIE_KEY: ebrains_login.user_token.access_token})
        ebrains_login.set_cookie(response)
        return response

    async def serve_service_worker(self, request: web.Request) -> web.StreamResponse:
        requested_url = get_requested_url(request)
        redirect_url = requested_url.updated_with(path=requested_url.path.parent.joinpath("public/js/service_worker.js"))
        raise web.HTTPFound(location=redirect_url.raw)

    async def welcome(self, request: web.Request) -> web.Response:
        redirect_url = get_requested_url(request).joinpath("public/html/welcome.html")
        raise web.HTTPFound(location=redirect_url.raw)

    @require_ebrains_login
    async def login_then_open_viewer(self, ebrains_login: EbrainsLogin, request: web.Request) -> web.Response:
        redirect_url = get_requested_url(request).updated_with(path=PurePosixPath("/public/nehuba/index.html"), hash_='!%7B"layout":"xy"%7D')
        raise web.HTTPFound(location=redirect_url.raw)

    def _make_compute_session_url(self, compute_session_id: uuid.UUID) -> Url:
        return self.external_url.joinpath(f"session-{compute_session_id}")

    @require_ebrains_login
    async def hello(self, ebrains_login: EbrainsLogin, request: web.Request) -> web.Response:
        return web.json_response("hello!", status=200)

    async def check_login(self, request: web.Request) -> web.Response:
        ebrains_login = await EbrainsLogin.from_cookie(request, http_client_session=self.http_client_session, oidc_client=self.oidc_client)
        if ebrains_login is None:
            return uncachable_json_response(
                CheckLoginResultDto(logged_in=False).to_json_value(),
                status=200
            )
        response = uncachable_json_response(
            CheckLoginResultDto(logged_in=True).to_json_value(),\
            status=200
        )
        ebrains_login.set_cookie(response=response)
        return response

    @require_ebrains_login
    async def login_then_close(self, ebrains_login: EbrainsLogin, request: web.Request) -> web.Response:
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
    async def create_compute_session(self, ebrains_login: EbrainsLogin, request: web.Request) -> web.Response:
        raw_payload = await request.content.read()
        json_payload = json.loads(raw_payload.decode('utf8'))
        params = CreateComputeSessionParamsDto.from_json_value(json_payload)
        if isinstance(params, MessageParsingError) or params.hpc_site not in self.session_launchers:
            return uncachable_json_response(RpcErrorDto(error="Bad payload").to_json_value(), status=400)
        requested_session_resources = Minutes(params.session_duration_minutes) * ComputeNodes(1) #FIXME: allow setting num compute modes

        user_info = await ebrains_login.user_token.get_userinfo(self.http_client_session)
        if isinstance(user_info, Exception):
            return uncachable_json_response(
                RpcErrorDto(error= "Could not retrieve user info").to_json_value(),
                status=400
            )

        async with self.quotas_lock:
            if user_info.sub not in self.session_user_locks:
                self.session_user_locks[user_info.sub] = asyncio.Lock()

        session_launcher = self.session_launchers[params.hpc_site]
        async with self.session_user_locks[user_info.sub]:
            this_months_jobs_result = await session_launcher.get_compute_sessions(
                user_id=user_info.sub, starttime=datetime.today().replace(day=1)
            )
            if isinstance(this_months_jobs_result, Exception):
                print(f"Could not get session information:\n{this_months_jobs_result}\n", file=sys.stderr)
                return uncachable_json_response(
                    RpcErrorDto(error= "Could not get session information").to_json_value(),
                    status=500
                )
            for job in this_months_jobs_result:
                if job.is_runnable():
                    return uncachable_json_response(
                        RpcErrorDto(error= f"Already running a session ({job.compute_session_id})").to_json_value(),
                        status=400
                    )
            used_quota = ComputeSession.compute_used_quota(this_months_jobs_result)
            monthly_quota = NodeHours(30) #FIXME: 30 is a totally arbitrary, hard-coded value
            available_quota = (monthly_quota.to_node_seconds() - used_quota)
            if available_quota.to_node_minutes() < requested_session_resources:
                return uncachable_json_response(
                    RpcErrorDto(error=f". Requested {requested_session_resources}node*min, only {available_quota.to_node_minutes()}node*min available").to_json_value(),
                    status=400
                )

            compute_session_id = uuid.uuid4()

            #############################################################
            # import subprocess
            # print(f">>>>>>>>>>>>>> Opening tunnel to app.ilastik.org....")
            # _tunnel_process = subprocess.run(
            #     [
            #         "ssh", "-fnNT",
            #         "-oBatchMode=yes",
            #         "-oExitOnForwardFailure=yes",
            #         "-oControlPersist=yes",
            #         "-M", "-S", f"/tmp/session-{compute_session_id}.control",
            #         "-L", f"/tmp/to-session-{compute_session_id}:/tmp/to-session-{compute_session_id}",
            #         f"www-data@148.187.149.187",
            #     ],
            # )
            # await asyncio.sleep(1)
            # print(f"<<<<<<<<<<<<< Hopefully it worked? sesion id is {compute_session_id}")
            # if _tunnel_process.returncode != 0 or not Path(f"/tmp/to-session-{compute_session_id}").exists():
            #     return uncachable_json_response(
            #         RpcErrorDto(error="Could not forward ports i think").to_json_value(),
            #         status=500
            #     )

            ###################################################################

            server_config = SessionAllocatorConfig.get()

            session_result = await session_launcher.launch(
                user_id=user_info.sub,
                compute_session_id=compute_session_id,
                allow_local_fs=server_config.allow_local_fs,
                ebrains_oidc_client=server_config.ebrains_oidc_client,
                ebrains_user_token=ebrains_login.user_token,
                max_duration_minutes=Minutes(params.session_duration_minutes),
                session_allocator_host=Hostname("app.ilastik.org"),
                session_allocator_username=Username("www-data"),#Username(getpass.getuser()),
                session_allocator_socket_path=Path(f"/tmp/to-session-{compute_session_id}"),
                session_url=self._make_compute_session_url(compute_session_id=compute_session_id),
            )

            if isinstance(session_result, Exception):
                print(f"Could not create compute session:\n{session_result}", file=sys.stderr)
                return uncachable_json_response(
                    RpcErrorDto(error="Could not create compute session").to_json_value(),
                    status=500
                )

            return uncachable_json_response(
                ComputeSessionStatusDto(
                    compute_session=session_result.to_dto(),
                    session_url=self._make_compute_session_url(compute_session_id).to_dto(),
                    connected=False,
                    hpc_site=params.hpc_site,
                ).to_json_value(),
                status=201,
            )

    @require_ebrains_login
    async def get_session_status(self, ebrains_login: EbrainsLogin, request: web.Request) -> web.Response:
        raw_payload = await request.content.read()
        json_payload = json.loads(raw_payload.decode('utf8'))
        params = GetComputeSessionStatusParamsDto.from_json_value(json_payload)
        if isinstance(params, MessageParsingError) or params.hpc_site not in self.session_launchers:
            return uncachable_json_response(RpcErrorDto(error="Bad payload").to_json_value(), status=400)
        user_info_result = await ebrains_login.user_token.get_userinfo(self.http_client_session)
        compute_session_id = uuid.UUID(params.compute_session_id) #FIXME: check parsing error?
        if isinstance(user_info_result, Exception):
            print(f"Error retrieving user info: {user_info_result}")
            return uncachable_json_response(
                RpcErrorDto(error="Could not get user information").to_json_value(),
                status=500  #FIXME: 500?
            )
        session_launcher = self.session_launchers[params.hpc_site]
        session_result = await session_launcher.get_compute_session_by_id(compute_session_id=compute_session_id, user_id=user_info_result.sub)
        if isinstance(session_result, Exception):
            return uncachable_json_response(
                RpcErrorDto(error="Could not retrieve session").to_json_value(),
                status=500
            )
        if session_result is None:
            return uncachable_json_response(
                RpcErrorDto(error="Session not found").to_json_value(),
                status=404
            )

        session_url = self._make_compute_session_url(compute_session_id=compute_session_id)

        #################################################################################
        # import subprocess
        # print(f">>>>>>>>>>>>>> Checking if tunnel socket exists on app.ilastik.org....")
        # tunnel_exists_check = subprocess.run(
        #     [
        #         "ssh",
        #         "-T",
        #         "-oBatchMode=yes",
        #         f"www-data@148.187.149.187",
        #         "ls", f"/tmp/to-session-{compute_session_id}"
        #     ],
        # )
        # if tunnel_exists_check.returncode != 0:
        #     print(f"Tunnel was not ready in web server")
        #     return uncachable_json_response(
        #         ComputeSessionStatusDto(
        #             compute_session=session_result.to_dto(),
        #             session_url=session_url.to_dto(),
        #             connected=False,
        #             hpc_site=params.hpc_site
        #         ).to_json_value(),
        #         status=200
        #     )
        ##################################################################################

        return uncachable_json_response(
            ComputeSessionStatusDto(
                compute_session=session_result.to_dto(),
                hpc_site=params.hpc_site,
                session_url=session_url.to_dto(),
                connected=await self.check_session_connection_state(session_result),
            ).to_json_value(),
            status=200
        )

    @require_ebrains_login
    async def close_session(self, ebrains_login: EbrainsLogin, request: web.Request) -> web.Response:
        raw_payload = await request.content.read()
        json_payload = json.loads(raw_payload.decode('utf8'))
        params = CloseComputeSessionParamsDto.from_json_value(json_payload)
        if isinstance(params, MessageParsingError) or params.hpc_site not in self.session_launchers:
            return uncachable_json_response(
                RpcErrorDto(error= "Bad payload").to_json_value(),
                status=400
            )
        compute_session_id = uuid.UUID(params.compute_session_id) #FIXME: check parsing error?
        session_launcher = self.session_launchers[params.hpc_site]

        user_info_result = await ebrains_login.user_token.get_userinfo(self.http_client_session)
        if isinstance(user_info_result, Exception):
            print(f"Error retrieving user info: {user_info_result}")
            return uncachable_json_response(
                RpcErrorDto(error="Could not get user information").to_json_value(),
                status=500  #FIXME: 500?
            )
        session_result = await session_launcher.get_compute_session_by_id(compute_session_id=compute_session_id, user_id=user_info_result.sub)
        if isinstance(session_result, Exception):
            return uncachable_json_response(
                RpcErrorDto(error="Could not retrieve session").to_json_value(),
                status=500
            )
        if session_result is None:
            return uncachable_json_response(
                RpcErrorDto(error="Session not found").to_json_value(),
                status=404
            )
        cancellation_result = await session_launcher.cancel(session_result)
        if isinstance(cancellation_result, Exception):
            return uncachable_json_response(
                RpcErrorDto(error=f"Failed to cancel session {compute_session_id}").to_json_value(),
                status=500
            )
        return uncachable_json_response(
            CloseComputeSessionResponseDto(compute_session_id=str(compute_session_id)).to_json_value(),
            status=200
        )

    async def check_session_connection_state(self, job: ComputeSession) -> bool:
        if job.is_done() or not Path(f"/tmp/to-session-{job.compute_session_id}").exists():
            return False
        session_url = self._make_compute_session_url(compute_session_id=job.compute_session_id)
        ping_session_result = await self.http_client_session.get(session_url.concatpath("status").raw)
        return ping_session_result.ok

    @require_ebrains_login
    async def list_sessions(self, ebrains_login: EbrainsLogin, request: web.Request) -> web.Response:
        json_payload = json.loads((await request.content.read()))
        params = ListComputeSessionsParamsDto.from_json_value(json_payload)
        if isinstance(params, MessageParsingError) or params.hpc_site not in self.session_launchers:
            return uncachable_json_response(
                RpcErrorDto(error= "Bad payload").to_json_value(),
                status=400
            )
        session_launcher = self.session_launchers[params.hpc_site]

        user_info_result = await ebrains_login.user_token.get_userinfo(self.http_client_session)
        if isinstance(user_info_result, Exception):
            print(f"Error retrieving user info: {user_info_result}")
            return uncachable_json_response(RpcErrorDto(error="Could not get user information").to_json_value(), status=500) #FIXME: 500?
        compute_sessions_result = await session_launcher.get_compute_sessions(
            user_id=user_info_result.sub, starttime=datetime.today().replace(day=1),
        )
        if isinstance(compute_sessions_result, Exception):
            return uncachable_json_response(RpcErrorDto(error="Could not retrieve sessions").to_json_value(), status=500)
        session_stati: List[ComputeSessionStatusDto] = []
        for comp_session in compute_sessions_result:
            session_stati.append(
                ComputeSessionStatusDto(
                    compute_session=comp_session.to_dto(),
                    session_url=self._make_compute_session_url(comp_session.compute_session_id).to_dto(),
                    connected=await self.check_session_connection_state(comp_session),
                    hpc_site=params.hpc_site,
                )
            )

        return uncachable_json_response(
            ListComputeSessionsResponseDto(compute_sessions_stati=tuple(ss for ss in session_stati)).to_json_value(),
            status=200
        )

    async def get_available_hpc_sites(self, request: web.Request) -> web.Response:
        return uncachable_json_response(
            GetAvailableHpcSitesResponseDto(
                available_sites=tuple(launcher_site for launcher_site in self.session_launchers.keys()),
            ).to_json_value(),
            status=200
        )

    def run(self, port: int):
        web.run_app(self.app, port=port) #type: ignore

if __name__ == '__main__':
    server_config = SessionAllocatorConfig.get()

    SessionAllocator(
        fernet=server_config.fernet,
        external_url=server_config.external_url,
        oidc_client=server_config.ebrains_oidc_client,
        allow_local_sessions=server_config.allow_local_compute_sessions
    ).run(port=5000)
