# pyright: reportUnusedCallResult=false

from asyncio.events import AbstractEventLoop
from concurrent.futures import Executor
from dataclasses import dataclass
from functools import partial
import multiprocessing
import os
import signal
import asyncio
from typing import Callable, Final, List, Optional, Tuple
import json
from base64 import b64decode
import ssl
import contextlib
from pathlib import Path, PurePosixPath
import traceback
import re
import datetime

import aiohttp
from aiohttp import web
from aiohttp.client import ClientSession
from aiohttp.http_websocket import WSCloseCode
from aiohttp.web_app import Application
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString

from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksInfo
from webilastik.filesystem.bucket_fs import BucketFs
from webilastik.scheduling.job import PriorityExecutor
from webilastik.server.session_allocator import uncachable_json_response
from webilastik.ui.datasource import try_get_datasources_from_url
from webilastik.ui.usage_error import UsageError
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow
from webilastik.utility.url import Protocol, Url
from webilastik.server.tunnel import ReverseSshTunnel
from webilastik.ui.applet import dummy_prompt
from webilastik.libebrains.user_token import UserToken
from webilastik.libebrains.slurm_job_launcher import Minutes
from executor_getter import get_executor


class MyLogger:
    def debug(self, message: str):
        print(f"\033[32m [DEBUG]{message}\033[0m")

    def info(self, message: str):
        print(f"\033[34m [INFO]{message}\033[0m")

    def warn(self, message: str):
        print(f"\033[33m [WARNING]{message}\033[0m")

    def error(self, message: str):
        print(f"\033[31m [ERROR]{message}\033[0m")


logger = MyLogger()

@dataclass
class RPCPayload:
    applet_name: str
    method_name: str
    arguments: JsonObject

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "RPCPayload":
        value_obj = ensureJsonObject(value)
        return RPCPayload(
            applet_name=ensureJsonString(value_obj.get("applet_name")),
            method_name=ensureJsonString(value_obj.get("method_name")),
            arguments=ensureJsonObject(value_obj.get("arguments")),
        )

    def to_json_value(self) -> JsonObject:
        return {
            "applet_name": self.applet_name,
            "method_name": self.method_name,
            "arguments": self.arguments,
        }

def do_save_project(filesystem: BucketFs, file_path: PurePosixPath, workflow_contents: bytes):
    with filesystem.openbin(file_path.as_posix(), "w") as f:
        f.write(workflow_contents)

def do_load_project_bytes(filesystem: BucketFs, file_path: PurePosixPath) -> bytes:
    with filesystem.openbin(file_path.as_posix(), "r") as f:
        return f.read()

class WebIlastik:
    @property
    def http_client_session(self) -> ClientSession:
        if self._http_client_session is None:
            self._http_client_session = aiohttp.ClientSession()
        return self._http_client_session

    @property
    def loop(self) -> AbstractEventLoop:
        if self._loop == None:
            self._loop = self.app.loop
        return self._loop

    def enqueue_user_interaction(self, user_interaction: Callable[[], Optional[UsageError]]):
        async def do_rpc():
            error_message = None
            try:
                result = user_interaction()
                if isinstance(result, UsageError):
                    error_message = str(result)
            except Exception as e:
                traceback_messages = traceback.format_exc()
                error_message = f"Unhandled Exception: {e}\n\n{traceback_messages}"
                logger.error(error_message)
            self._update_clients(error_message=error_message)
        self.loop.call_soon_threadsafe(lambda: self.loop.create_task(do_rpc()))

    async def close_websockets(self, app: Application):
        for ws in self.websockets:
            await ws.close(
                code=WSCloseCode.GOING_AWAY,
                message=json.dumps({
                    "error": 'Server shutdown'
                }).encode("utf8")
            )

    def __init__(
        self,
        *,
        max_duration_minutes: Minutes,
        session_url: Url,
        executor: Executor,
        ssl_context: Optional[ssl.SSLContext] = None
    ):
        super().__init__()

        self.start_time_utc: Final[datetime.datetime] = datetime.datetime.now(datetime.timezone.utc)
        self.max_duration_minutes = max_duration_minutes
        self.session_url = session_url
        self.ssl_context = ssl_context
        self.websockets: List[web.WebSocketResponse] = []
        self._http_client_session: Optional[ClientSession] = None
        self._loop: Optional[AbstractEventLoop] = None

        self.executor = executor
        self.priority_executor = PriorityExecutor(executor=self.executor, max_active_job_steps=2 * multiprocessing.cpu_count())

        self.workflow = PixelClassificationWorkflow(
            on_async_change=lambda : self.enqueue_user_interaction(lambda: None), #FIXME?
            executor=self.executor,
            priority_executor=self.priority_executor
        )
        self.app = web.Application()
        self.app.add_routes([
            web.get('/status', self.get_status),
            web.get('/ws', self.open_websocket),
            web.get(
                "/predictions/raw_data={encoded_raw_data}/generation={generation}/data/{xBegin}-{xEnd}_{yBegin}-{yEnd}_{zBegin}-{zEnd}",
                lambda request: self.workflow.pixel_classifier_applet.precomputed_chunks_compute(request)
            ),
            web.get(
                "/predictions/raw_data={encoded_raw_data}/generation={generation}/info",
                lambda request: self.workflow.pixel_classifier_applet.predictions_precomputed_chunks_info(request)
            ),
            web.post("/download_project_as_ilp", self.download_project_as_ilp),
            web.delete("/close", self.close_session),
            web.get(
                "/stripped_precomputed/url={encoded_original_url}/resolution={resolution_x}_{resolution_y}_{resolution_z}/info",
                self.stripped_precomputed_info
            ),
            web.get(
                "/stripped_precomputed/url={encoded_original_url}/resolution={resolution_x}_{resolution_y}_{resolution_z}/{rest:.*}",
                self.forward_chunk_request
            ),
            web.post(
                "/get_datasources_from_url",
                self.get_datasources_from_url
            ),
            web.post(
                "/save_project",
                self.save_project
            ),
            web.post(
                "/load_project",
                self.load_project
            ),
        ])
        self.app.on_shutdown.append(self.close_websockets)

    async def get_datasources_from_url(self, request: web.Request) -> web.Response:
        payload = await request.json()
        raw_url = payload.get("url")
        if raw_url is None:
            return  web.json_response({"error", "Missing 'url' key in payload"}, status=400)
        url = Url.parse(raw_url)
        if url is None:
            return  web.json_response({"error", "Bad url in payload"}, status=400)

        selected_resolution: "Tuple[int, int, int] | None" = None
        stripped_precomputed_url_regex = re.compile(r"/stripped_precomputed/url=(?P<url>[^/]+)/resolution=(?P<resolution>\d+_\d+_\d+)")
        match = stripped_precomputed_url_regex.search(url.path.as_posix())
        if match:
            url = Url.from_base64(match.group("url"))
            selected_resolution = tuple(int(axis) for axis in match.group("resolution").split("_"))

        datasources_result = try_get_datasources_from_url(url=url, allowed_protocols=(Protocol.HTTP, Protocol.HTTPS))
        if isinstance(datasources_result, Exception):
            return web.json_response({"error": str(datasources_result)}, status=400)
        if isinstance(datasources_result, type(None)):
            return uncachable_json_response({"error": f"Unsupported datasource type: {url}"}, status=400)
        if selected_resolution:
            datasources = [ds for ds in datasources_result if ds.spatial_resolution == selected_resolution]
            if len(datasources) != 1:
                return web.json_response({
                    "error": f"Expected single datasource, found these: {json.dumps([ds.to_json_value() for ds in datasources], indent=4)}"
                })
        else:
            datasources = datasources_result

        return web.json_response({
            "datasources": tuple([ds.to_json_value() for ds in datasources])
        })

    async def get_status(self, request: web.Request) -> web.Response:
        return uncachable_json_response(
            {
                "status": "running",
                "start_time_utc": self.start_time_utc.timestamp(),
                "max_duration_minutes": self.max_duration_minutes,
            },
            status=200
        )

    async def close_session(self, request: web.Request) -> web.Response:
        #FIXME: this is not properly killing the server
        _ = asyncio.get_event_loop().create_task(self._self_destruct())
        return web.Response()

    async def _self_destruct(self, after_seconds: int = 5):
        _ = await asyncio.sleep(after_seconds)
        self.priority_executor.shutdown()
        self.executor.shutdown()
        try:
            pid = os.getpid()
            pgid = os.getpgid(pid)
            logger.info(f"[SESSION KILL]Gently killing local session (pid={pid}) with SIGINT on group....")
            os.killpg(pgid, signal.SIGINT)
            _ = await asyncio.sleep(10)
            logger.info(f"[SESSION KILL]Killing local session (pid={pid}) with SIGKILL on group....")
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def run(self, host: Optional[str] = None, port: Optional[int] = None, unix_socket_path: Optional[str] = None):
        web.run_app(self.app, port=port, path=unix_socket_path)

    async def open_websocket(self, request: web.Request):
        websocket = web.WebSocketResponse()
        _ = await websocket.prepare(request)
        self.websockets.append(websocket)
        logger.debug(f"JUST STABILISHED A NEW CONNECTION!!!! {len(self.websockets)}")
        self._update_clients() # when a new client connects, send it the current state
        async for msg in websocket:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close':
                    _ = await websocket.close()
                    continue
                try:
                    parsed_payload = json.loads(msg.data)
                    logger.debug(f"Got new rpc call:\n{json.dumps(parsed_payload, indent=4)}\n")
                    payload = RPCPayload.from_json_value(parsed_payload)
                    logger.debug("GOT PAYLOAD OK")
                    user_interaction = partial(
                        self.workflow.run_rpc,
                        user_prompt=dummy_prompt,
                        applet_name=payload.applet_name,
                        method_name=payload.method_name,
                        arguments=payload.arguments,
                    )
                    self.enqueue_user_interaction(user_interaction)
                except Exception:
                    import traceback
                    traceback.print_exc()
                    self._update_clients() # restore last known good state of offending client
            elif msg.type == aiohttp.WSMsgType.BINARY:
                logger.error(f'Unexpected binary message')
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f'ws connection closed with exception {websocket.exception()}')
        if websocket in self.websockets:
            logger.info(f"Removing websocket! Current websockets: {len(self.websockets)}")
            self.websockets.remove(websocket)
        logger.info('websocket connection closed')
        return websocket

    async def do_update(self, payload: JsonValue):
        stringified_payload = json.dumps(payload)
        for websocket in self.websockets[:]:
            try:
                # FIXME: do all sockets at once
                await websocket.send_str(stringified_payload)
            except ConnectionResetError as e:
                logger.error(f"Got an exception while updating remote:\n{e}\n\nRemoving websocket...")
                self.websockets.remove(websocket)

    def _update_clients(self, error_message: Optional[str] = None):
        loop = self.app.loop # FIXME?
        if error_message is not None:
            loop.create_task(self.do_update({"error": error_message}))
        payload = self.workflow.get_json_state()
        loop.create_task(self.do_update(payload))

    async def download_project_as_ilp(self, request: web.Request):
        return web.Response(
            body=self.workflow.get_ilp_contents(),
            content_type="application/octet-stream",
            headers={
                "Content-disposition": 'attachment; filename="MyProject.ilp"'
            }
        )

    async def save_project(self, request: web.Request) -> web.Response:
        payload = await request.json()
        filesystem = BucketFs.from_json_value(payload.get("fs"))
        file_path = PurePosixPath(ensureJsonString(payload.get("project_file_path")))
        if len(file_path.parts) == 0 or ".." in file_path.parts:
            return web.Response(status=400, text=f"Bad project file path: {file_path}")

        await asyncio.wrap_future(self.executor.submit(
            do_save_project,
            filesystem=filesystem,
            file_path=file_path,
            workflow_contents=self.workflow.get_ilp_contents()
        ))

        return web.Response(status=200, text=f"Project saved to {filesystem.geturl(file_path.as_posix())}")

    async def load_project(self, request: web.Request) -> web.Response:
        payload = await request.json()
        filesystem = BucketFs.from_json_value(payload.get("fs"))
        file_path = PurePosixPath(ensureJsonString(payload.get("project_file_path")))
        if len(file_path.parts) == 0 or ".." in file_path.parts:
            return web.Response(status=400, text=f"Bad project file path: {file_path}")

        ilp_bytes = await asyncio.wrap_future(self.executor.submit(
            do_load_project_bytes,
            filesystem=filesystem,
            file_path=file_path,
        ))
        new_workflow_result = PixelClassificationWorkflow.from_ilp_bytes(
            ilp_bytes=ilp_bytes,
            on_async_change=lambda : self.enqueue_user_interaction(lambda: None), #FIXME?
            executor=self.executor,
            priority_executor=self.priority_executor,
            allowed_protocols=(Protocol.HTTP, Protocol.HTTPS),
        )
        if isinstance(new_workflow_result, Exception):
            return web.Response(status=400, text=f"Could not load project: {new_workflow_result}")
        self.workflow = new_workflow_result
        self._update_clients()
        return web.Response(status=200, text=f"Project saved to {filesystem.geturl(file_path.as_posix())}")

    async def stripped_precomputed_info(self, request: web.Request) -> web.Response:
        """Serves a precomp info stripped of all but one scales"""
        resolution_x = request.match_info.get("resolution_x")
        resolution_y = request.match_info.get("resolution_y")
        resolution_z = request.match_info.get("resolution_z")
        if resolution_x is None or resolution_y is None or resolution_z is None:
            return web.Response(status=400, text=f"Bad resolution: {resolution_x}_{resolution_y}_{resolution_z}")
        try:
            resolution = (int(resolution_x), int(resolution_y), int(resolution_z))
        except Exception:
            return web.Response(status=400, text=f"Bad resolution: {resolution_x}_{resolution_y}_{resolution_z}")

        encoded_original_url = request.match_info.get("encoded_original_url")
        if not encoded_original_url:
            return web.Response(status=400, text="Missing parameter: url")

        decoded_url = b64decode(encoded_original_url, altchars=b'-_').decode('utf8')
        base_url = Url.parse(decoded_url)
        if base_url is None:
            return web.Response(status=400, text=f"Bad url: {decoded_url}")
        info_url = base_url.joinpath("info")
        logger.debug(f"Will request this info: {info_url.schemeless_raw}")

        token = UserToken.get_global_login_token()
        if isinstance(token, UsageError):
            return web.Response(status=403, text="Token has expired") # FIXME

        async with self.http_client_session.get(
            info_url.schemeless_raw,
            ssl=self.ssl_context,
            headers=token.as_auth_header() if info_url.hostname == "data-proxy.ebrains.eu" else {},
            params={"redirect": "true"} if info_url.hostname == "data-proxy.ebrains.eu" else {},
        ) as response:
            response_text = await response.text()
            if response.status // 100 != 2:
                return web.Response(status=response.status, text=response_text)
            info = PrecomputedChunksInfo.from_json_value(json.loads(response_text))

        stripped_info = info.stripped(resolution=resolution)
        return web.json_response(stripped_info.to_json_value())

    async def forward_chunk_request(self, request: web.Request) -> web.Response:
        """Redirects a precomp chunk request to the original URL"""
        encoded_original_url = request.match_info.get("encoded_original_url")
        if not encoded_original_url:
            return web.Response(status=400, text="Missing parameter: url")
        decoded_url = b64decode(encoded_original_url, altchars=b'-_').decode('utf8')
        url = Url.parse(decoded_url)
        if url is None:
            return web.Response(status=400, text=f"Bad url: {decoded_url}")
        rest = request.match_info.get("rest", "").lstrip("/")
        tile_url = url.joinpath(rest)

        if tile_url.hostname != "data-proxy.ebrains.eu":
            raise web.HTTPFound(location=tile_url.schemeless_raw)

        token = UserToken.get_global_login_token()
        if isinstance(token, UsageError):
            return web.Response(status=403, text="Token has expired") # FIXME

        async with self.http_client_session.get(
            tile_url.schemeless_raw,
            ssl=self.ssl_context,
            headers=token.as_auth_header(),
        ) as response:
            cscs_url = (await response.json())["url"]
            raise web.HTTPFound(location=cscs_url)


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--max-duration-minutes", type=int, required=True, help="Number of minutes this workflow can run for")
    parser.add_argument("--ebrains-user-access-token", type=str, required=True)
    parser.add_argument("--listen-socket", type=Path, required=True)
    parser.add_argument("--session-url", required=True)


    subparsers = parser.add_subparsers(required=False, help="tunnel stuff")
    tunnel_parser = subparsers.add_parser("tunnel", help="Creates a reverse tunnel to an orchestrator")
    tunnel_parser.add_argument("--remote-username", type=str, required=True)
    tunnel_parser.add_argument("--remote-host", required=True)
    tunnel_parser.add_argument("--remote-unix-socket", type=Path, required=True)

    args = parser.parse_args()

    session_url = Url.parse_or_raise(args.session_url)
    UserToken.login_globally(token=UserToken(access_token=args.ebrains_user_access_token))

    executor = get_executor(hint="server_tile_handler", max_workers=multiprocessing.cpu_count())

    if "remote_username" in vars(args):
        server_context = ReverseSshTunnel(
            remote_username=args.remote_username,
            remote_host=args.remote_host,
            remote_unix_socket=args.remote_unix_socket,
            local_unix_socket=args.listen_socket,
        )
    else:
        server_context = contextlib.nullcontext()


    with server_context:
        WebIlastik(
            executor=executor,
            max_duration_minutes=Minutes(args.max_duration_minutes),
            session_url=session_url,
        ).run(
            unix_socket_path=str(args.listen_socket),
        )
    try:
        os.remove(args.listen_socket)
    except FileNotFoundError:
        pass

