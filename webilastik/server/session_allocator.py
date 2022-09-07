# pyright: reportUnusedCallResult=false

from functools import wraps
import json
from typing import Any, Callable, Coroutine, Dict, NoReturn, Optional
from pathlib import Path, PurePosixPath
import uuid
import asyncio
import sys
from datetime import datetime
import subprocess
from dataclasses import dataclass

from aiohttp import web
import aiohttp
from aiohttp.client import ClientSession
from cryptography.fernet import Fernet
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonInt, ensureJsonObject
from webilastik.libebrains.slurm_job_launcher import CscsSshJobLauncher, JobState, JusufSshJobLauncher, Minutes, NodeSeconds, Seconds, SlurmJob, SlurmJobId, SshJobLauncher

from webilastik.libebrains.user_token import UserToken
from webilastik.libebrains.oidc_client import OidcClient, Scope
from webilastik.utility.url import Url, Protocol as UrlProtocol


def get_requested_url(request: web.Request) -> Url:
    protocol = UrlProtocol.from_str(request.headers['X-Forwarded-Proto'])
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
    AUTH_COOKIE_KEY = "ebrains_user_access_token"

    def __init__(self, user_token: UserToken):
        self.user_token = user_token
        super().__init__()

    @classmethod
    async def from_cookie(cls, request: web.Request, http_client_session: ClientSession) -> Optional["EbrainsLogin"]:
        access_token = request.cookies.get(cls.AUTH_COOKIE_KEY)
        if access_token is None:
            return None
        user_token = UserToken(access_token=access_token)
        if not await user_token.is_valid(http_client_session):
            return None
        return EbrainsLogin(user_token=user_token)

    @classmethod
    async def from_code(cls, request: web.Request, oidc_client: OidcClient, http_client_session: ClientSession) -> Optional["EbrainsLogin"]:
        auth_code = request.query.get("code")
        if auth_code is None:
            return None
        user_token = await oidc_client.get_user_token(
            code=auth_code, redirect_uri=get_requested_url(request), http_client_session=http_client_session
        )
        return EbrainsLogin(user_token=user_token)

    @classmethod
    async def try_from_request(cls, request: web.Request, oidc_client: OidcClient, http_client_session: ClientSession) -> Optional["EbrainsLogin"]:
        return (
            (await cls.from_cookie(request, http_client_session=http_client_session)) or
            (await EbrainsLogin.from_code(request, oidc_client=oidc_client, http_client_session=http_client_session))
        )

    def set_cookie(self, response: web.Response) -> web.Response:
        response.set_cookie(
            name=self.AUTH_COOKIE_KEY, value=self.user_token.access_token, secure=True
        )
        return response


def require_ebrains_login(
    endpoint: Callable[["SessionAllocator", EbrainsLogin, web.Request], Coroutine[Any, Any, web.Response]]
) -> Callable[["SessionAllocator", web.Request], Coroutine[Any, Any, web.Response]]:

    @wraps(endpoint)
    async def wrapper(self: "SessionAllocator", request: web.Request) -> web.Response:
        ebrains_login = await EbrainsLogin.try_from_request(
            request, oidc_client=self.oidc_client, http_client_session=self.http_client_session
        )
        if ebrains_login is None:
            redirect_to_ebrains_login(request, oidc_client=self.oidc_client)
        response = await endpoint(self, ebrains_login, request)
        return ebrains_login.set_cookie(response)

    return wrapper

@dataclass
class SessionStatus:
    slurm_job: SlurmJob
    session_url: Url
    connected: bool

    def to_json_value(self) -> JsonObject:
        return {
            "slurm_job": self.slurm_job.to_json_value(),
            "session_url": self.session_url.to_json_value(),
            "connected": self.connected,
        }

class SessionAllocator:
    def __init__(
        self,
        *,
        session_launcher: SshJobLauncher,
        external_url: Url,
        oidc_client: OidcClient,
    ):
        self.session_launcher: SshJobLauncher = session_launcher
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
            web.post('/api/session', self.spawn_session),
            web.get('/api/session/{session_id}', self.session_status),
            web.delete('/api/session/{session_id}', self.close_session),
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
            return web.json_response({"error": f"Bad origin: {origin}"}, status=400)
        session = await EbrainsLogin.from_cookie(request, http_client_session=self.http_client_session)
        if session is None:
            return web.json_response({"error": f"Not logged in"}, status=400)
        return web.json_response({EbrainsLogin.AUTH_COOKIE_KEY: session.user_token.access_token})

    async def serve_service_worker(self, request: web.Request) -> web.StreamResponse:
        requested_url = get_requested_url(request)
        redirect_url = requested_url.updated_with(path=requested_url.path.parent.joinpath("public/js/service_worker.js"))
        raise web.HTTPFound(location=redirect_url.raw)

    async def welcome(self, request: web.Request) -> web.Response:
        redirect_url = get_requested_url(request).joinpath("public/html/welcome.html")
        raise web.HTTPFound(location=redirect_url.raw)

    @require_ebrains_login
    async def login_then_open_viewer(self, ebrains_login: EbrainsLogin, request: web.Request) -> web.Response:
        redirect_url = get_requested_url(request).updated_with(path=PurePosixPath("/public/nehuba/index.html"))
        raise web.HTTPFound(location=redirect_url.raw)

    def _make_session_url(self, session_id: uuid.UUID) -> Url:
        return self.external_url.joinpath(f"session-{session_id}")

    @require_ebrains_login
    async def hello(self, ebrains_login: EbrainsLogin, request: web.Request) -> web.Response:
        return web.json_response("hello!", status=200)

    async def check_login(self, request: web.Request) -> web.Response:
        if (await EbrainsLogin.from_cookie(request, http_client_session=self.http_client_session)) is None:
            return web.json_response({"logged_in": False}, status=401)
        return web.json_response({"logged_in": True}, status=200)

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
    async def spawn_session(self, ebrains_login: EbrainsLogin, request: web.Request) -> web.Response:
        raw_payload = await request.content.read()
        try:
            payload_dict = ensureJsonObject(json.loads(raw_payload.decode('utf8')))
            requested_duration_minutes = Minutes(ensureJsonInt(payload_dict.get("session_duration_minutes")))
        except Exception:
            return web.json_response({"error": "Bad payload"}, status=400)

        user_info = await ebrains_login.user_token.get_userinfo(self.http_client_session)
        if isinstance(user_info, Exception):
            return web.json_response({"error": "Could not retrieve user info"}, status=400)
        if user_info.sub != uuid.UUID("bdca269c-f207-4cdb-8b68-a562e434faed"): #FIXME
            return web.json_response({"error": "This user can't allocate sessions yet"}, status=400)

        async with self.quotas_lock:
            if user_info.sub not in self.session_user_locks:
                self.session_user_locks[user_info.sub] = asyncio.Lock()

        async with self.session_user_locks[user_info.sub]:
            this_months_jobs_result = await self.session_launcher.get_jobs(
                user_id=user_info.sub, starttime=datetime.today().replace(day=1)
            )
            if isinstance(this_months_jobs_result, Exception):
                print(f"Could not get session information:\n{this_months_jobs_result}\n", file=sys.stderr)
                return web.json_response({"error": "Could not get session information"}, status=500)
            for job in this_months_jobs_result:
                if job.is_runnable():
                    return web.json_response({"error": f"Already running a session ({job.session_id})"}, status=400)
            used_quota_node_sec = SlurmJob.compute_used_quota(this_months_jobs_result)
            monthly_quota_node_sec: NodeSeconds = NodeSeconds(100 * 60 * 60) #FIXME
            available_quota_node_min = (monthly_quota_node_sec - used_quota_node_sec) / 60
            if available_quota_node_min < 0: #FIXME
                return web.json_response({
                    "error": f"Not enough quota. Requested {requested_duration_minutes}min, only {available_quota_node_min}min available"
                },
                status=400
            )

            session_id = uuid.uuid4()

            #############################################################
            # print(f">>>>>>>>>>>>>> Opening tunnel to app.ilastik.org....")
            # _tunnel_process = subprocess.run(
            #     [
            #         "ssh", "-fnNT",
            #         "-oBatchMode=yes",
            #         "-oExitOnForwardFailure=yes",
            #         "-oControlPersist=yes",
            #         "-M", "-S", f"/tmp/session-{session_id}.control",
            #         "-L", f"/tmp/to-session-{session_id}:/tmp/to-session-{session_id}",
            #         f"www-data@148.187.149.187",
            #     ],
            # )
            # await asyncio.sleep(1)
            # print(f"<<<<<<<<<<<<< Hopefully it worked? sesion id is {session_id}")
            # if _tunnel_process.returncode != 0 or not Path(f"/tmp/to-session-{session_id}").exists():
            #     return uncachable_json_response({"error": "Could not forward ports i think"}, status=500)

            ###################################################################

            session_result = await self.session_launcher.launch(
                user_id=user_info.sub,
                time=Minutes(min(
                    int(available_quota_node_min), int(requested_duration_minutes)
                )),
                ebrains_user_token=ebrains_login.user_token,
                session_id=session_id,
            )

            if isinstance(session_result, Exception):
                print(f"Could not create compute session:\n{session_result}", file=sys.stderr)
                return web.json_response({"error": "Could not create compute session"}, status=500)

            return web.json_response(
                SessionStatus(
                    slurm_job=session_result, session_url=self._make_session_url(session_id), connected=False
                ).to_json_value(),
                status=201,
            )

    @require_ebrains_login
    async def session_status(self, ebrains_login: EbrainsLogin, request: web.Request) -> web.Response:
        # FIXME: do security checks here?
        try:
            session_id =  uuid.UUID(request.match_info.get("session_id"))
        except Exception:
            return uncachable_json_response({"error": "Bad session id"}, status=400)
        user_info_result = await ebrains_login.user_token.get_userinfo(self.http_client_session)
        if isinstance(user_info_result, Exception):
            print(f"Error retrieving user info: {user_info_result}")
            return uncachable_json_response({"error": "Could not get user information"}, status=500) #FIXME: 500?
        session_result = await self.session_launcher.get_job_by_session_id(session_id=session_id, user_id=user_info_result.sub)
        if isinstance(session_result, Exception):
            return uncachable_json_response({"error": "Could not retrieve session"}, status=500)
        if session_result is None:
            return uncachable_json_response({"error": "Session not found"}, status=404)

        session_url = self._make_session_url(session_id=session_id)

        #################################################################################
        # print(f">>>>>>>>>>>>>> Checking if tunnel socket exists on app.ilastik.org....")
        # tunnel_exists_check = subprocess.run(
        #     [
        #         "ssh",
        #         "-T",
        #         "-oBatchMode=yes",
        #         f"www-data@148.187.149.187",
        #         "ls", f"/tmp/to-session-{session_id}"
        #     ],
        # )
        # if tunnel_exists_check.returncode != 0:
        #     print(f"Tunnel was not ready in web server")
        #     return uncachable_json_response(
        #         SessionStatus(
        #             slurm_job=session_result, session_url=session_url, connected=False
        #         ).to_json_value(),
        #         status=200
        #     )
        ##################################################################################

        ping_session_result = await self.http_client_session.get(session_url.concatpath("status").raw)
        print(f"Ping session result: {ping_session_result.status}   ok? {ping_session_result.ok}", file=sys.stderr)
        print(f"Tunnel file exists? {Path(f'/tmp/to-session-{session_id}').exists()}")

        import datetime
        return uncachable_json_response(
            SessionStatus(
                slurm_job=session_result,
                # slurm_job=SlurmJob(
                #     job_id=SlurmJobId(123),
                #     user_id=user_info_result.sub,
                #     state=JobState.RUNNING,
                #     start_time_utc_sec=Seconds(int(datetime.datetime.now(datetime.timezone.utc).timestamp())),
                #     num_nodes=1,
                #     time_elapsed_sec=Seconds(1),
                #     time_limit_minutes=Minutes(99999),
                #     session_id=session_id,
                # ),
                session_url=session_url,
                connected=ping_session_result.ok and Path(f"/tmp/to-session-{session_id}").exists(),
            ).to_json_value(),
            status=200
        )

    @require_ebrains_login
    async def close_session(self, ebrains_login: EbrainsLogin, request: web.Request) -> web.Response:
        # FIXME: do security checks here?
        try:
            session_id =  uuid.UUID(request.match_info.get("session_id"))
        except Exception:
            return uncachable_json_response({"error": "Bad session id"}, status=400)
        user_info_result = await ebrains_login.user_token.get_userinfo(self.http_client_session)
        if isinstance(user_info_result, Exception):
            print(f"Error retrieving user info: {user_info_result}")
            return uncachable_json_response({"error": "Could not get user information"}, status=500) #FIXME: 500?
        session_result = await self.session_launcher.get_job_by_session_id(session_id=session_id, user_id=user_info_result.sub)
        if isinstance(session_result, Exception):
            return uncachable_json_response({"error": "Could not retrieve session"}, status=500)
        if session_result is None:
            return uncachable_json_response({"error": "Session not found"}, status=404)
        cancellation_result = await self.session_launcher.cancel(session_result)
        if isinstance(cancellation_result, Exception):
            return uncachable_json_response({"error": f"Failed to cancel session {session_id}"}, status=500)
        return uncachable_json_response({"session_id": str(session_id)}, status=200)

    def run(self, port: int):
        web.run_app(self.app, port=port)

if __name__ == '__main__':
    from argparse import ArgumentParser
    import os
    fernet = Fernet(key=os.environ["WEBILASTIK_SESSION_ALLOCATOR_FERNET_KEY"].encode('utf8'))
    parser = ArgumentParser()
    parser.add_argument("--session-launcher", choices=["JUSUF", "CSCS"], required=True)
    parser.add_argument("--external-url", type=Url.parse, required=True, help="Url from which sessions can be accessed (where the session sockets live)")
    parser.add_argument(
        "--oidc-client-json",
        help="Path to a json file representing the keycloak client or the special value 'skip'. You can get this data via OidcClient.get"
    )

    args = parser.parse_args()

    # multiprocessing.set_start_method('spawn') #start a fresh interpreter so it doesn't 'inherit' the event loop
    if args.session_launcher == "JUSUF":
        session_launcher = JusufSshJobLauncher(fernet=fernet)
    elif args.session_launcher == "CSCS":
        session_launcher = CscsSshJobLauncher(fernet=fernet)
    else:
        print(f"Can get a session launcher for {args.session_launcher}")
        exit(1)

    with open(args.oidc_client_json) as f:
        oidc_client = OidcClient.from_json_value(json.load(f))

    SessionAllocator(
        session_launcher=session_launcher,
        external_url=args.external_url,
        oidc_client=oidc_client,
    ).run(port=5000)
