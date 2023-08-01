# pyright: reportUnusedCallResult=false

from asyncio.events import AbstractEventLoop
from concurrent.futures import Executor
from dataclasses import dataclass
from functools import partial
import multiprocessing
import os
import signal
import asyncio
import tempfile
from typing import Callable, Final, List, Optional
import json
import ssl
from pathlib import PurePosixPath, Path
import traceback
import datetime

import aiohttp
from aiohttp import web
from aiohttp.client import ClientSession
from aiohttp.http_websocket import WSCloseCode
from aiohttp.web_app import Application
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString
from webilastik.classic_ilastik.ilp.pixel_classification_ilp import IlpPixelClassificationWorkflowGroup

from webilastik.filesystem import FsFileNotFoundException, FsIoException, IFilesystem, create_filesystem_from_message, create_filesystem_from_url
from webilastik.filesystem.os_fs import OsFs
from webilastik.scheduling.job import PriorityExecutor
from webilastik.server.rpc.dto import (
    GetDatasourcesFromUrlParamsDto,
    GetDatasourcesFromUrlResponseDto,
    GetFileSystemAndPathFromUrlParamsDto,
    GetFileSystemAndPathFromUrlResponseDto,
    ListFsDirRequest,
    ListFsDirResponse,
    LoadProjectParamsDto,
    MessageParsingError,
    RpcErrorDto,
    SaveProjectParamsDto,
)
from webilastik.server.session_allocator import uncachable_json_response
from webilastik.ui.datasource import try_get_datasources_from_url
from webilastik.ui.usage_error import UsageError
from webilastik.ui.workflow.pixel_classification_workflow import WsPixelClassificationWorkflow
from webilastik.utility.url import Url
from webilastik.server.tunnel import ReverseSshTunnel
from webilastik.ui.applet import dummy_prompt
from webilastik.libebrains.compute_session_launcher import Minutes
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

def do_save_project(filesystem: IFilesystem, file_path: PurePosixPath, workflow_contents: bytes) -> "None | FsIoException":
    return filesystem.create_file(path=file_path, contents=workflow_contents)

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

        self.workflow = WsPixelClassificationWorkflow(
            on_async_change=lambda: self.enqueue_user_interaction(user_interaction=lambda: None), #FIXME?
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
            web.post(
                "/get_datasources_from_url",
                self.get_datasources_from_url
            ),
            web.post(
                "/try_get_fs_and_path_from_url",
                self.try_get_fs_and_path_from_url
            ),
            web.post(
                "/check_datasource_compatibility",
                lambda request: self.workflow.pixel_classifier_applet.check_datasource_compatibility(request)
            ),
            web.post(
                "/save_project",
                self.save_project
            ),
            web.post(
                "/load_project",
                self.load_project
            ),
            web.post(
                "/list_fs_dir",
                self.list_fs_dir,
            ),
        ])
        self.app.on_shutdown.append(self.close_websockets)

    async def list_fs_dir(self, request: web.Request) -> web.Response:
        params_result = ListFsDirRequest.from_json_value(await request.json())
        if isinstance(params_result, MessageParsingError):
            return uncachable_json_response(RpcErrorDto(error=str(params_result)).to_json_value(), status=400)
        fs_result = create_filesystem_from_message(params_result.fs)
        if isinstance(fs_result, Exception):
            return uncachable_json_response(RpcErrorDto(error="Could not create filesystem").to_json_value(), status=400)
        items_result = fs_result.list_contents(path=PurePosixPath(params_result.path))
        if isinstance(items_result, Exception):
            return uncachable_json_response(
                RpcErrorDto(error=str(items_result)).to_json_value(),
                status=400,
            )
        return uncachable_json_response(
            ListFsDirResponse(
                files=tuple(str(f) for f in items_result.files),
                directories=tuple(str(d) for d in items_result.directories),
            ).to_json_value(),
            status=200,
        )

    async def get_datasources_from_url(self, request: web.Request) -> web.Response:
        params = GetDatasourcesFromUrlParamsDto.from_json_value(await request.json())
        if isinstance(params, MessageParsingError):
            return  uncachable_json_response(RpcErrorDto(error="bad payload").to_json_value(), status=400)
        url = Url.from_dto(params.url)

        datasources_result = await asyncio.wrap_future(self.executor.submit(
            try_get_datasources_from_url, url=url,
        ))
        if isinstance(datasources_result, Exception):
            return uncachable_json_response(RpcErrorDto(error=str(datasources_result)).to_json_value(), status=400)
        if isinstance(datasources_result, type(None)):
            return uncachable_json_response(GetDatasourcesFromUrlResponseDto(datasources=None).to_json_value(), status=400)
        return uncachable_json_response(
            GetDatasourcesFromUrlResponseDto(datasources=tuple([ds.to_dto() for ds in datasources_result])).to_json_value(),
            status=200,
        )

    async def try_get_fs_and_path_from_url(self, request: web.Request) -> web.Response:
        params = GetFileSystemAndPathFromUrlParamsDto.from_json_value(await request.json())
        if isinstance(params, MessageParsingError):
            return  uncachable_json_response(RpcErrorDto(error="bad payload").to_json_value(), status=400)
        url = Url.from_dto(params.url)

        result = await asyncio.wrap_future(self.executor.submit(
            create_filesystem_from_url, url=url,
        ))
        if isinstance(result, Exception):
            return uncachable_json_response(RpcErrorDto(error=str(result)).to_json_value(), status=400)
        fs, path = result
        return uncachable_json_response(
            GetFileSystemAndPathFromUrlResponseDto(
                fs=fs.to_dto(),
                path=path.as_posix(),
            ).to_json_value(),
            status=200,
        )

    async def get_status(self, request: web.Request) -> web.Response:
        return uncachable_json_response(
            {
                "status": "running",
                "start_time_utc": self.start_time_utc.timestamp(),
                "max_duration_minutes": self.max_duration_minutes.to_int(),
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
        params_result = SaveProjectParamsDto.from_json_value(payload)
        if isinstance(params_result, MessageParsingError):
            return web.Response(status=400, text=f"Bad payload")
        fs_result = create_filesystem_from_message(params_result.fs)
        if isinstance(fs_result, Exception):
            return uncachable_json_response(RpcErrorDto(error=str(fs_result)).to_json_value(), status=400)
        file_path = PurePosixPath(params_result.project_file_path)
        if len(file_path.parts) == 0 or ".." in file_path.parts:
            return web.Response(status=400, text=f"Bad project file path: {file_path}")

        saving_result = await asyncio.wrap_future(self.executor.submit(
            do_save_project,
            filesystem=fs_result,
            file_path=file_path,
            workflow_contents=self.workflow.get_ilp_contents()
        ))
        if isinstance(saving_result, Exception):
            return uncachable_json_response(
                RpcErrorDto(error=str(saving_result)).to_json_value(),
                status=400, #FIXME?
            )
        return web.Response(status=200, text=f"Project saved to {fs_result.geturl(file_path)}")

    async def load_project(self, request: web.Request) -> web.Response:
        payload = await request.json()
        params_result = LoadProjectParamsDto.from_json_value(payload)
        if isinstance(params_result, MessageParsingError):
            return uncachable_json_response(RpcErrorDto(error="Could not parse message").to_json_value(), status=400)
        input_fs_result = create_filesystem_from_message(params_result.fs)
        if isinstance(input_fs_result, Exception):
            return uncachable_json_response(RpcErrorDto(error=str(input_fs_result)).to_json_value(), status=400)
        file_path = PurePosixPath(params_result.project_file_path)
        if len(file_path.parts) == 0 or ".." in file_path.parts:
            return uncachable_json_response(RpcErrorDto(error="Bad path").to_json_value(), status=400)

        if isinstance(input_fs_result, OsFs):
            ilp_fs = input_fs_result
            ilp_path = file_path
        else:
            ilp_path = PurePosixPath("temp_ilp_project.ilp")
            ilp_fs_result = OsFs.create_scratch_dir()
            if isinstance(ilp_fs_result, Exception):
                print(ilp_fs_result)
                return uncachable_json_response(RpcErrorDto(error="Could not donwload ilp: no osfs permission").to_json_value(), status=400)
            ilp_fs = ilp_fs_result

            transfer_result = await asyncio.wrap_future(self.executor.submit(
                ilp_fs.transfer_file,
                source_fs=input_fs_result, source_path=file_path, target_path=ilp_path
            ))
            if isinstance(transfer_result, Exception):
                print(ilp_fs_result)
                return uncachable_json_response(RpcErrorDto(error="Could not donwload ilp").to_json_value(), status=400)

        group_result = await asyncio.wrap_future(self.executor.submit(
            IlpPixelClassificationWorkflowGroup.from_file,
            ilp_fs=ilp_fs, path=ilp_path
        ))
        if isinstance(group_result, Exception):
            print(group_result)
            return uncachable_json_response(RpcErrorDto(error=f"Could not parse ilp: {group_result}").to_json_value(), status=400)

        new_workflow_result =  WsPixelClassificationWorkflow.from_ilp(
            workflow_group=group_result,
            on_async_change=lambda: self.enqueue_user_interaction(user_interaction=lambda: None), #FIXME?
            executor=self.executor,
            priority_executor=self.priority_executor,
        )
        self.workflow = new_workflow_result
        self._update_clients()
        return web.Response(status=200)

if __name__ == '__main__':
    from webilastik.config import WorkflowConfig
    workflow_config = WorkflowConfig.get()

    executor = get_executor(hint="server_tile_handler", max_workers=multiprocessing.cpu_count())

    server_context = ReverseSshTunnel(
        remote_username=workflow_config.session_allocator_username,
        remote_host=workflow_config.session_allocator_host,
        remote_unix_socket=workflow_config.session_allocator_socket_path,
        local_unix_socket=workflow_config.listen_socket,
    )

    with server_context:
        WebIlastik(
            executor=executor,
            max_duration_minutes=workflow_config.max_duration_minutes,
            session_url=workflow_config.session_url,
        ).run(
            unix_socket_path=str(workflow_config.listen_socket),
        )
    try:
        os.remove(workflow_config.listen_socket)
    except FileNotFoundError:
        pass

