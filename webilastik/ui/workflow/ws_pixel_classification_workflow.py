# pyright: reportUnusedCallResult=false


from abc import abstractmethod
from asyncio.tasks import Task
from dataclasses import dataclass
import os
import signal
import asyncio
import threading
from typing import Any, Dict, Iterable, List, Optional, Mapping, Sequence, Tuple
import json
from base64 import b64decode
import ssl
import uuid
from aiohttp import web
import numpy as np
import contextlib
from pathlib import Path
import time

import aiohttp
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonArray, ensureJsonBoolean, ensureJsonObject, ensureJsonString

from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksInfo
from webilastik.ui.applet.datasource_batch_processing_applet import PixelClasificationExportingApplet
from webilastik.ui.datasink import DataSinkCreationParams
from webilastik.ui.datasource import DataSourceLoadParams
from webilastik.ui.usage_error import UsageError
from webilastik.utility.url import Url
from webilastik.scheduling.hashing_executor import HashingExecutor, Job
from webilastik.datasource import DataSource
from webilastik.server.tunnel import ReverseSshTunnel
from webilastik.datasource import DataRoi
from webilastik.features.channelwise_fastfilters import (
    StructureTensorEigenvalues,
    GaussianGradientMagnitude,
    GaussianSmoothing,
    DifferenceOfGaussians,
    HessianOfGaussianEigenvalues,
    LaplacianOfGaussian,
)
from webilastik.annotations.annotation import Annotation
from webilastik.features.ilp_filter import IlpFilter
from webilastik.annotations import Annotation
from webilastik.ui.applet import Applet, AppletOutput, PropagationError, PropagationOk, PropagationResult, UserPrompt, dummy_prompt
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.brushing_applet import BrushingApplet
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow
from webilastik.libebrains.user_token import UserToken


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

def _decode_datasource(datasource_json_b64_altchars_dash_underline: str) -> DataSource:
    json_str = b64decode(datasource_json_b64_altchars_dash_underline.encode('utf8'), altchars=b'-_').decode('utf8')
    return DataSource.from_json_value(json.loads(json_str))

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

class WsApplet(Applet):
    @abstractmethod
    def _get_json_state(self) -> JsonValue:
        pass

    @abstractmethod
    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        ...

class WsBrushingApplet(WsApplet, BrushingApplet):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.brushing_enabled = False

    def _get_json_state(self) -> JsonValue:
        return {
            "annotations": tuple(annotation.to_json_data() for annotation in self.annotations()),
            "brushing_enabled": self.brushing_enabled,
        }

    def set_brushing_enabled(self, enabled: bool) -> PropagationResult:
        self.brushing_enabled = enabled
        return PropagationOk()

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        if method_name == "brushing_enabled":
            enabled = ensureJsonBoolean(arguments.get("enabled"))
            return UsageError.check(self.set_brushing_enabled(enabled=enabled))

        raw_annotations = ensureJsonArray(arguments.get("annotations"))
        annotations = [Annotation.from_json_value(raw_annotation) for raw_annotation in raw_annotations]

        if method_name == "add_annotations":
            return UsageError.check(self.add_annotations(user_prompt, annotations))
        if method_name == "remove_annotations":
            return UsageError.check(self.remove_annotations(user_prompt, annotations))

        raise ValueError(f"Invalid method name: '{method_name}'")


class WsFeatureSelectionApplet(WsApplet, FeatureSelectionApplet):
    def _item_from_json_data(self, data: JsonValue) -> IlpFilter:
        data_dict = ensureJsonObject(data)
        class_name = ensureJsonString(data_dict.get("__class__"))
        if class_name == StructureTensorEigenvalues.__name__:
            return StructureTensorEigenvalues.from_json_data(data)
        if class_name == GaussianGradientMagnitude.__name__:
            return GaussianGradientMagnitude.from_json_data(data)
        if class_name == GaussianSmoothing.__name__:
            return GaussianSmoothing.from_json_data(data)
        if class_name == DifferenceOfGaussians.__name__:
            return DifferenceOfGaussians.from_json_data(data)
        if class_name == HessianOfGaussianEigenvalues.__name__:
            return HessianOfGaussianEigenvalues.from_json_data(data)
        if class_name == LaplacianOfGaussian.__name__:
            return LaplacianOfGaussian.from_json_data(data)
        raise ValueError(f"Could not convert {data} into a Feature Extractor")

    def _get_json_state(self) -> JsonValue:
        return {"feature_extractors": tuple(extractor.to_json_data() for extractor in self.feature_extractors())}

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        raw_feature_array = ensureJsonArray(arguments.get("feature_extractors"))
        feature_extractors = [self._item_from_json_data(raw_feature) for raw_feature in raw_feature_array]

        if method_name == "add_feature_extractors":
            return UsageError.check(self.add_feature_extractors(dummy_prompt, feature_extractors))
        if method_name == "remove_feature_extractors":
            return UsageError.check(self.remove_feature_extractors(user_prompt, feature_extractors))
        raise ValueError(f"Invalid method name: '{method_name}'")


class WsPixelClassificationApplet(WsApplet, PixelClassificationApplet):
    def __init__(
        self,
        name: str,
        *,
        feature_extractors: AppletOutput[Sequence[IlpFilter]],
        annotations: AppletOutput[Sequence[Annotation]],
        runner: HashingExecutor,
    ):
        self.runner = runner
        super().__init__(name=name, feature_extractors=feature_extractors, annotations=annotations)

    def _get_json_state(self) -> JsonValue:
        classifier = self.pixel_classifier()
        if classifier:
            channel_colors = tuple(color.to_json_data() for color in classifier.color_map.keys())
        else:
            channel_colors = tuple()

        return {
            "producer_is_ready": classifier is not None,
            "channel_colors": channel_colors,
        }

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        raise ValueError(f"Invalid method name: '{method_name}'")

    async def predictions_precomputed_chunks_info(self, request: web.Request) -> web.Response:
        classifier = self.pixel_classifier()
        if classifier is None:
            return web.json_response({"error": "Classifier is not ready yet"}, status=412)

        encoded_raw_data_url = str(request.match_info.get("encoded_raw_data"))
        datasource = _decode_datasource(encoded_raw_data_url)

        return web.Response(
            text=json.dumps({
                "@type": "neuroglancer_multiscale_volume",
                "type": "image",
                "data_type": "uint8",  # DONT FORGET TO CONVERT PREDICTIONS TO UINT8!
                "num_channels": classifier.num_classes,
                "scales": [
                    {
                        "key": "data",
                        "size": [int(v) for v in datasource.shape.to_tuple("xyz")],
                        "resolution": datasource.spatial_resolution,
                        "voxel_offset": [0, 0, 0],
                        "chunk_sizes": [datasource.tile_shape.to_tuple("xyz")],
                        "encoding": "raw",
                    }
                ],
            }),
            headers={
                "Cache-Control": "no-store, must-revalidate",
                "Expires": "0",
            },
            content_type="application/json",
        )

    async def precomputed_chunks_compute(self, request: web.Request) -> web.Response:
        encoded_raw_data = str(request.match_info.get("encoded_raw_data")) # type: ignore
        xBegin = int(request.match_info.get("xBegin")) # type: ignore
        xEnd = int(request.match_info.get("xEnd")) # type: ignore
        yBegin = int(request.match_info.get("yBegin")) # type: ignore
        yEnd = int(request.match_info.get("yEnd")) # type: ignore
        zBegin = int(request.match_info.get("zBegin")) # type: ignore
        zEnd = int(request.match_info.get("zEnd")) # type: ignore

        datasource = _decode_datasource(encoded_raw_data)
        classifier = self.pixel_classifier()
        if classifier is None:
            return web.json_response({"error": "Classifier is not ready yet"}, status=412)

        predictions = await asyncio.wrap_future(self.runner.submit(
            classifier.compute,
            DataRoi(datasource, x=(xBegin, xEnd), y=(yBegin, yEnd), z=(zBegin, zEnd))
        ))

        if "format" in request.query:
            requested_format = request.query["format"]
            if requested_format != "png":
                return web.Response(status=400, text="Server-side rendering only available in png, not in {requested_format}")
            if predictions.shape.z > 1:
                return web.Response(status=400, text="Server-side rendering only available for 2d images")

            prediction_png_bytes = list(predictions.to_z_slice_pngs())[0]
            return web.Response(
                body=prediction_png_bytes.getbuffer(),
                headers={
                    "Cache-Control": "no-store, must-revalidate",
                    "Expires": "0",
                },
                content_type="image/png",
            )

        # https://github.com/google/neuroglancer/tree/master/src/neuroglancer/datasource/precomputed#raw-chunk-encoding
        # "(...) data for the chunk is stored directly in little-endian binary format in [x, y, z, channel] Fortran order"
        resp = predictions.as_uint8().raw("xyzc").tobytes("F")
        return web.Response(
            body=resp,
            content_type="application/octet-stream",
        )

@dataclass
class PixelExportRequest:
    data_source_params: DataSourceLoadParams
    data_sink_params: DataSinkCreationParams

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "PixelExportRequest":
        value_obj = ensureJsonObject(value)
        return PixelExportRequest(
            data_source_params=DataSourceLoadParams.from_json_value(value_obj.get("data_source_params")),
            data_sink_params=DataSinkCreationParams.from_json_value(value_obj.get("data_sink_params")),
        )

class WsExportApplet(WsApplet, PixelClasificationExportingApplet):
    def __init__(
        self,
        *,
        name: str,
        executor: HashingExecutor,
        pixel_classifier: AppletOutput[Optional[VigraPixelClassifier[IlpFilter]]],
        ebrains_user_token: UserToken,
    ):
        self.jobs: Dict[uuid.UUID, Job[Any]] = {}
        self.ebrains_user_token = ebrains_user_token
        self.lock = threading.Lock()
        self.last_update = time.monotonic()
        super().__init__(name=name, executor=executor, classifier=pixel_classifier)

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        if method_name == "start_export_job":
            classifier = self._in_classifier()
            if classifier is None:
                return UsageError("Classifier not ready yet")

            pixel_export_request = PixelExportRequest.from_json_value(arguments)

            raw_data = pixel_export_request.data_source_params.try_load(ebrains_user_token=self.ebrains_user_token)
            if isinstance(raw_data, UsageError):
                return raw_data

            sink = pixel_export_request.data_sink_params.try_load(
                ebrains_user_token=self.ebrains_user_token,
                dtype=np.dtype("float32"),
                location=raw_data.location,
                interval=raw_data.interval.updated(c=(0, classifier.num_classes)),
                chunk_size=raw_data.tile_shape,
                spatial_resolution=raw_data.spatial_resolution,
            )
            if isinstance(sink, UsageError):
                return sink

            def on_job_step_completed(job_id: uuid.UUID, step_index: int):
                logger.debug(f"** Job step {job_id}:{step_index} done")
                self._mark_updated()

            def on_job_completed(job_id: uuid.UUID):
                logger.debug(f"**** Job {job_id} completed")
                self._mark_updated()

            job = self.start_export_job(
                user_prompt=dummy_prompt,
                source=raw_data,
                sink=sink,
                on_progress=on_job_step_completed,
                on_complete=on_job_completed,
            )
            self.jobs[job.uuid] = job

            logger.info(f"Started job {job.uuid}")
            return None
        if method_name == "cancel_job":
            job_id = uuid.UUID(ensureJsonString(arguments.get("job_id")))
            self.executor.cancel_group(job_id)
            _ = self.jobs.pop(job_id, None)
            return None
        raise ValueError(f"Invalid method name: '{method_name}'")

    def _mark_updated(self):
        with self.lock:
            self.last_update = time.monotonic()

    def get_updated_status(self, last_seen_update: float) -> Tuple[float, Optional[JsonObject]]:
        with self.lock:
            if last_seen_update < self.last_update:
                return (self.last_update, self._get_json_state())
            return (self.last_update, None)

    def _get_json_state(self) -> JsonObject:
        return {
            "jobs": tuple(job.to_json_value() for job in self.jobs.values())
        }


class WsPixelClassificationWorkflow(PixelClassificationWorkflow):
    async def update_remote_jobs(self):
        last_seen_update = 0
        while True:
            await asyncio.sleep(1)
            last_seen_update, applet_status = self.export_applet.get_updated_status(last_seen_update)
            if applet_status is not None:
                logger.warn(f"Updating jobs status")
                await self._update_clients_state(applets=[self.export_applet])

    def __init__(self, ebrains_user_token: UserToken, ssl_context: Optional[ssl.SSLContext] = None):
        self.ssl_context = ssl_context
        self.ebrains_user_token = ebrains_user_token
        self.websockets: List[web.WebSocketResponse] = []
        self.job_updater_task: Optional[Task[Any]] = None

        executor = HashingExecutor(name="Pixel Classification Executor")

        brushing_applet = WsBrushingApplet("brushing_applet")
        feature_selection_applet = WsFeatureSelectionApplet("feature_selection_applet", datasources=brushing_applet.datasources)
        pixel_classifier_applet = WsPixelClassificationApplet(
            "pixel_classification_applet",
            feature_extractors=feature_selection_applet.feature_extractors,
            annotations=brushing_applet.annotations,
            runner=executor,
        )

        self.export_applet = WsExportApplet(
            name="export_applet",
            executor=executor,
            pixel_classifier=pixel_classifier_applet.pixel_classifier,
            ebrains_user_token=ebrains_user_token,
        )

        self.wsapplets : Mapping[str, WsApplet] = {
            feature_selection_applet.name: feature_selection_applet,
            brushing_applet.name: brushing_applet,
            pixel_classifier_applet.name: pixel_classifier_applet,
            self.export_applet.name: self.export_applet,
        }

        super().__init__(
            feature_selection_applet=feature_selection_applet,
            brushing_applet=brushing_applet,
            pixel_classifier_applet=pixel_classifier_applet,
        )

        self.app = web.Application()
        self.app.add_routes([
            web.get('/status', self.get_status),
            web.get('/ws', self.open_websocket), # type: ignore
            web.get(
                "/predictions/raw_data={encoded_raw_data}/run_id={run_id}/data/{xBegin}-{xEnd}_{yBegin}-{yEnd}_{zBegin}-{zEnd}",
                pixel_classifier_applet.precomputed_chunks_compute
            ),
            web.get(
                "/predictions/raw_data={encoded_raw_data}/run_id={run_id}/info",
                pixel_classifier_applet.predictions_precomputed_chunks_info
            ),
            web.post("/ilp_project", self.ilp_download),
            web.delete("/close", self.close_session),
            web.get(
                "/stripped_precomputed/url={encoded_original_url}/resolution={resolution_x}_{resolution_y}_{resolution_z}/info",
                self.stripped_precomputed_info
            ),
            web.get(
                "/stripped_precomputed/url={encoded_original_url}/resolution={resolution_x}_{resolution_y}_{resolution_z}/{rest:.*}",
                self.forward_chunk_request
            ),
        ])

    async def get_status(self, request: web.Request) -> web.Response:
        return web.Response(
            text=json.dumps({
                "status": "running"
            }),
            content_type="application/json",
        )

    async def close_session(self, request: web.Request) -> web.Response:
        #FIXME: this is not properly killing the server
        _ = asyncio.get_event_loop().create_task(self._self_destruct())
        return web.Response()

    async def _self_destruct(self, after_seconds: int = 5):
        _ = await asyncio.sleep(5)
        try:
            pid = os.getpid()
            pgid = os.getpgid(pid)
            # logger.info(f"Gently killing local session (pid={pid}) with SIGINT on group....")
            # os.killpg(pgid, signal.SIGINT)
            # _ = await asyncio.sleep(10)
            logger.info(f"Killing local session (pid={pid}) with SIGKILL on group....")
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def run(self, host: Optional[str] = None, port: Optional[int] = None, unix_socket_path: Optional[str] = None):
        web.run_app(self.app, port=port, path=unix_socket_path)

    async def open_websocket(self, request: web.Request):
        if self.job_updater_task is None:
            self.job_updater_task = asyncio.create_task(self.update_remote_jobs())
        websocket = web.WebSocketResponse()
        _ = await websocket.prepare(request)
        self.websockets.append(websocket)
        logger.debug(f"JUST STABILISHED A NEW CONNECTION!!!! {len(self.websockets)}")
        await self._update_clients_state([websocket]) # when a new client connects, send it the current state
        async for msg in websocket:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close':
                    _ = await websocket.close()
                    continue
                try:
                    parsed_payload = json.loads(msg.data)
                    logger.debug(f"Got new rpc call:\n{json.dumps(parsed_payload, indent=4)}\n")
                    payload = RPCPayload.from_json_value(parsed_payload)
                    await self._do_rpc(payload=payload, originator=websocket)
                except Exception as e:
                    logger.error(f"Exception happened on set state:\n{e}")
                    import traceback
                    traceback.print_exc()
                    await self._update_clients_state([websocket]) # restore last known good state of offending client
            elif msg.type == aiohttp.WSMsgType.BINARY:
                logger.error(f'Unexpected binary message')
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f'ws connection closed with exception {websocket.exception()}')
        if websocket in self.websockets:
            logger.info(f"Removing websocket! Current websockets: {len(self.websockets)}")
            self.websockets.remove(websocket)
        logger.info('websocket connection closed')
        return websocket

    async def _do_rpc(self, originator: web.WebSocketResponse, payload: RPCPayload):
        #FIXME: show bad results to user
        result = self.wsapplets[payload.applet_name].run_rpc(user_prompt=dummy_prompt, method_name=payload.method_name, arguments=payload.arguments)
        if isinstance(result, UsageError):
            logger.error(f"UsageError: {result}")
            await originator.send_json({"error": str(result)})
        await self._update_clients_state()

    async def _update_clients_state(self, websockets: Optional[Iterable[web.WebSocketResponse]] = None, applets: Optional[Iterable[WsApplet]] = None):
        ws = list(websockets) if websockets is not None else self.websockets
        logger.debug(f"Updating {len(ws)} clients")
        state : JsonObject = {
            applet.name: applet._get_json_state()
            for applet in (applets if applets is not None else self.wsapplets.values())
        }
        # logger.debug(f"Updating remote to following state:\n{json.dumps(state, indent=4)}")
        for websocket in ws:
            try:
                await websocket.send_str(json.dumps(state))
            except ConnectionResetError as e:
                logger.error(f"Got an exception while updating remote:\n{e}\n\nRemoving websocket...")
                self.websockets.remove(websocket)

    async def ilp_download(self, request: web.Request):
        return web.Response(
            body=self.ilp_file.read(),
            content_type="application/octet-stream",
            headers={
                "Content-disposition": 'attachment; filename="MyProject.ilp"'
            }
        )

    async def stripped_precomputed_info(self, request: web.Request) -> web.Response:
        """Serves a precomp info stripped of all but one scales"""
        resolution_x = request.match_info.get("resolution_x")
        resolution_y = request.match_info.get("resolution_y")
        resolution_z = request.match_info.get("resolution_z")
        if resolution_x is None or resolution_y is None or resolution_z is None:
            return web.Response(status=400, text=f"Bad resolution: {resolution_x}_{resolution_y}_{resolution_z}")
        try:
            resolution = (int(resolution_x), int(resolution_x), int(resolution_x))
        except Exception:
            return web.Response(status=400, text=f"Bad resolution: {resolution_x}_{resolution_y}_{resolution_z}")

        encoded_original_url = request.match_info.get("encoded_original_url")
        if not encoded_original_url:
            return web.Response(status=400, text="Missing parameter: url")

        info_url = Url.parse(b64decode(encoded_original_url, altchars=b'-_').decode('utf8')).joinpath("info")
        logger.debug(f"Will request this info: {info_url.schemeless_raw}")
        async with aiohttp.ClientSession() as session:
            async with session.get(info_url.schemeless_raw, ssl=self.ssl_context) as response:
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
        info_url = Url.parse(b64decode(encoded_original_url, altchars=b'-_').decode('utf8'))
        rest = request.match_info.get("rest", "").lstrip("/")
        raise web.HTTPFound(location=info_url.joinpath(rest).schemeless_raw)


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--ebrains-user-access-token", type=str, required=True)
    parser.add_argument("--listen-socket", type=Path, required=True)
    parser.add_argument("--ca-cert-path", "--ca_cert_path", help="Path to CA crt file. Useful e.g. for testing with mkcert")

    subparsers = parser.add_subparsers(required=False, help="tunnel stuff")
    tunnel_parser = subparsers.add_parser("tunnel", help="Creates a reverse tunnel to an orchestrator")
    tunnel_parser.add_argument("--remote-username", type=str, required=True)
    tunnel_parser.add_argument("--remote-host", required=True)
    tunnel_parser.add_argument("--remote-unix-socket", type=Path, required=True)

    args = parser.parse_args()

    mpi_rank = 0
    try:
        from mpi4py import MPI #type: ignore
        mpi_rank = MPI.COMM_WORLD.Get_rank()
    except ModuleNotFoundError:
        pass

    ca_crt: Optional[str] = args.ca_cert_path or os.environ.get("CA_CERT_PATH")
    ssl_context: Optional[ssl.SSLContext] = None

    if ca_crt is not None:
        if not Path(ca_crt).exists():
            logger.error(f"File not found: {ca_crt}")
            exit(1)
        ssl_context = ssl.create_default_context(cafile=ca_crt)

    if "remote_username" in vars(args) and mpi_rank == 0:
        server_context = ReverseSshTunnel(
            remote_username=args.remote_username,
            remote_host=args.remote_host,
            remote_unix_socket=args.remote_unix_socket,
            local_unix_socket=args.listen_socket,
        )
    else:
        server_context = contextlib.nullcontext()

    with server_context:
        WsPixelClassificationWorkflow(
            ebrains_user_token=UserToken(access_token=args.ebrains_user_access_token),
            ssl_context=ssl_context
        ).run(
            unix_socket_path=str(args.listen_socket),
        )
