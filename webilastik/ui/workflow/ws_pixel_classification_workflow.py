from abc import abstractmethod, ABC
import functools
import os
import signal
import asyncio
from typing import Any, Dict, List, Optional, Mapping, cast, Sequence
import json
from base64 import b64decode
from http import HTTPStatus

from ndstructs.datasource.PrecomputedChunksDataSource import PrecomputedChunksInfo
from ndstructs.utils.json_serializable import JsonValue, ensureJsonArray, ensureJsonObject, ensureJsonString
from webilastik.scheduling.hashing_executor import HashingExecutor

from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasource import datasource_from_url

from ndstructs.datasource.DataSource import DataSource
from webilastik.server.tunnel import ReverseSshTunnel
from pathlib import Path
import contextlib

import aiohttp
from aiohttp import web
from ndstructs.datasource.DataRoi import DataRoi

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
from webilastik.ui.applet import Applet, CONFIRMER, Slot
from webilastik.ui.applet.data_selection_applet import DataSelectionApplet
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.brushing_applet import BrushingApplet
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow, PixelClassificationLane


@functools.lru_cache()
def _decode_datasource(datasource_url_b64_altchars_dash_underline: str) -> DataSource:
    url = b64decode(datasource_url_b64_altchars_dash_underline.encode('utf8'), altchars=b'-_').decode('utf8')
    return datasource_from_url(url)


class WsAppletMixin(Applet):
    @property
    def websockets(self) -> List[web.WebSocketResponse]:
        if not hasattr(self,"_websockets"):
            self._websockets = cast(List[web.WebSocketResponse], [])
        return self._websockets

    @abstractmethod
    def _get_json_state(self) -> JsonValue:
        pass

    @abstractmethod
    def _set_json_state(self, state: JsonValue):
        pass

    async def _update_remote(self):
        bad_sockets : List[web.WebSocketResponse] = []
        for websocket in self.websockets:
            try:
                state = self._get_json_state()
                if state is not None:
                    print(f"\033[32m  Updating remote {self.name} to following state:\n{json.dumps(state, indent=4)}  \033[0m")
                    await websocket.send_str(json.dumps(state))
            except ConnectionResetError as e:
                print(f"!!!!!+++!!!! Got an exception while updating remote:\n{e}\n\nRemoving websocket...")
                bad_sockets.append(websocket)
        for bad_socket in bad_sockets:
            self.websockets.remove(bad_socket)

    async def _add_websocket(self, websocket: web.WebSocketResponse):
        self.websockets.append(websocket)
        await self._update_remote()
        async for msg in websocket:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close':
                    await websocket.close()
                else:
                    try:
                        payload = json.loads(msg.data)
                        print(f"\033[34m Got new state:\n{json.dumps(payload, indent=4)}\n \033[0m")
                        self._set_json_state(payload)
                    except Exception as e:
                        print(f"Exception happend on set state:\n\033[31m{e}\033[0m")
                        # FIXME: show some error message
                    finally:
                        await self._update_remote()
            elif msg.type == aiohttp.WSMsgType.BINARY:
                print(f'Unexpected binary message')
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(f'ws connection closed with exception {websocket.exception()}')
        self.websockets.remove(websocket)
        print('websocket connection closed')
        return websocket

    def post_refresh(self, confirmer: CONFIRMER): #FIXME: this will fire even if something breaks downstream
        super().post_refresh(confirmer)
        asyncio.get_event_loop().create_task(self._update_remote())

    def restore_snaphot(self, snap: Dict[str, Any]):
        super().restore_snaphot(snap)
        asyncio.get_event_loop().create_task(self._update_remote())


class WsBrushingApplet(WsAppletMixin, BrushingApplet):
    def _get_json_state(self) -> JsonValue:
        return tuple(annotation.to_json_data() for annotation in self.annotations.get() or [])

    def _set_json_state(self, state: JsonValue):
        raw_brush_array = ensureJsonArray(state)
        return self.annotations.set_value(
            [Annotation.from_json_data(raw_brush) for raw_brush in raw_brush_array],
            confirmer=lambda msg: True
        )


class WsFeatureSelectionApplet(WsAppletMixin, FeatureSelectionApplet):
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
        return tuple(extractor.to_json_data() for extractor in self.feature_extractors.get() or [])

    def _set_json_state(self, state: JsonValue):
        raw_feature_array = ensureJsonArray(state)
        return self.feature_extractors.set_value(
            [self._item_from_json_data(raw_feature) for raw_feature in raw_feature_array],
            confirmer=lambda msg: True
        )


class WsPredictingApplet(WsAppletMixin):
    def __init__(
        self,
        name: str,
        *,
        pixel_classifier: Slot[VigraPixelClassifier[IlpFilter]],
        datasources: Slot[Sequence[DataSource]],
        runner: HashingExecutor,
    ):
        self._in_pixel_classifier = pixel_classifier
        self._in_datasources = datasources
        self.runner = runner
        super().__init__(name=name)

    def _get_json_state(self) -> JsonValue:
        classifier = self._in_pixel_classifier.get()
        if classifier:
            producer_is_ready = True
            channel_colors = tuple(color.to_json_data() for color in classifier.color_map.keys())
        else:
            producer_is_ready = False
            channel_colors = tuple()

        return {
            "producer_is_ready": producer_is_ready,
            "channel_colors": channel_colors,
            "datasources": tuple(ds.to_json_data() for ds in self._in_datasources.get() or []),
        }

    def _set_json_state(self, state: JsonValue):
        pass

    async def predictions_precomputed_chunks_info(self, request: web.Request):
        classifier = self._in_pixel_classifier()
        expected_num_channels = len(classifier.color_map)
        encoded_raw_data_url = str(request.match_info.get("encoded_raw_data")) # type: ignore
        datasource = _decode_datasource(encoded_raw_data_url)

        return web.Response(
            text=json.dumps({
                "@type": "neuroglancer_multiscale_volume",
                "type": "image",
                "data_type": "uint8",  # DONT FORGET TO CONVERT PREDICTIONS TO UINT8!
                "num_channels": expected_num_channels,
                "scales": [
                    {
                        "key": "data",
                        "size": [int(v) for v in datasource.shape.to_tuple("xyz")],
                        "resolution": [1, 1, 1],
                        "voxel_offset": [0, 0, 0],
                        "chunk_sizes": [datasource.tile_shape.to_tuple("xyz")],
                        "encoding": "raw",
                    }
                ],
            }),
            headers={
                "Cache-Control": "no-store"
            },
            content_type="application/json",
        )

    async def precomputed_chunks_compute(self, request: web.Request) -> web.Response:
        encoded_raw_data_url = str(request.match_info.get("encoded_raw_data")) # type: ignore
        xBegin = int(request.match_info.get("xBegin")) # type: ignore
        xEnd = int(request.match_info.get("xEnd")) # type: ignore
        yBegin = int(request.match_info.get("yBegin")) # type: ignore
        yEnd = int(request.match_info.get("yEnd")) # type: ignore
        zBegin = int(request.match_info.get("zBegin")) # type: ignore
        zEnd = int(request.match_info.get("zEnd")) # type: ignore

        datasource = _decode_datasource(encoded_raw_data_url)
        predictions = await self.runner.async_submit(
            self._in_pixel_classifier().compute,
            DataRoi(datasource, x=(xBegin, xEnd), y=(yBegin, yEnd), z=(zBegin, zEnd))
        )

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
                    "Cache-Control": "no-store"
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


class WsPixelClassificationWorkflow(PixelClassificationWorkflow):
    def __init__(self):
        brushing_applet = WsBrushingApplet("brushing_applet")
        feature_selection_applet = WsFeatureSelectionApplet("feature_selection_applet", datasources=brushing_applet.datasources)
        pixel_classifier_applet = PixelClassificationApplet(
            "pixel_classification_applet",
            feature_extractors=feature_selection_applet.feature_extractors,
            annotations=brushing_applet.annotations,
        )
        predicting_applet = WsPredictingApplet(
            "predicting_applet",
            pixel_classifier=pixel_classifier_applet.pixel_classifier,
            datasources=brushing_applet.datasources,
            runner=HashingExecutor(num_workers=8),
        )
        self.ws_applets : Mapping[str, WsAppletMixin] = {
            feature_selection_applet.name: feature_selection_applet,
            brushing_applet.name: brushing_applet,
            predicting_applet.name: predicting_applet,
        }
        super().__init__(
            feature_selection_applet=feature_selection_applet,
            brushing_applet=brushing_applet,
            pixel_classifier_applet=pixel_classifier_applet,
        )

        self.app = web.Application()
        self.app.add_routes([
            web.get('/status', self.get_status),
            web.get('/ws/{applet_name}', self.open_websocket), # type: ignore
            web.get(
                "/predictions/raw_data={encoded_raw_data}/run_id={run_id}/data/{xBegin}-{xEnd}_{yBegin}-{yEnd}_{zBegin}-{zEnd}",
                predicting_applet.precomputed_chunks_compute
            ),
            web.get(
                "/predictions/raw_data={encoded_raw_data}/run_id={run_id}/info",
                predicting_applet.predictions_precomputed_chunks_info
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
        asyncio.get_event_loop().create_task(self._self_destruct())
        return web.Response()

    async def _self_destruct(self, after_seconds: int = 5):
        await asyncio.sleep(5)
        try:
            pid = os.getpid()
            pgid = os.getpgid(pid)
            print(f"===>>>> gently killing local session (pid={pid}) with SIGINT on group....")
            os.killpg(pgid, signal.SIGINT)
            await asyncio.sleep(10)
            print(f"===>>>> Killing local session (pid={pid}) with SIGKILL on group....")
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def run(self, host: Optional[str] = None, port: Optional[int] = None, unix_socket_path: Optional[str] = None):
        web.run_app(self.app, port=port, path=unix_socket_path)

    async def open_websocket(self, request: web.Request):
        applet_name = str(request.match_info.get("applet_name"))  # type: ignore
        if applet_name not in self.ws_applets:
            raise ValueError(f"Bad applet name: {applet_name}")
        applet = self.ws_applets[applet_name]
        websocket = web.WebSocketResponse()
        await websocket.prepare(request)
        return await applet._add_websocket(websocket)

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

        info_url = b64decode(encoded_original_url, altchars=b'-_').decode('utf8').lstrip("precomputed://").rstrip("/") + "/info"
        print(f"+++++ Will request this info: {info_url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(info_url) as response:
                response_text = await response.text()
                if response.status // 100 != 2:
                    return web.Response(status=response.status, text=response_text)
                info = PrecomputedChunksInfo.from_json_data(json.loads(response_text))

        stripped_info = PrecomputedChunksInfo(
            at_type=info.at_type,
            type_=info.type_,
            data_type=info.data_type,
            num_channels=info.num_channels,
            scales=tuple(scale for scale in info.scales if tuple(scale.resolution) == resolution),
        )
        return web.json_response(stripped_info.to_json_data())

    async def forward_chunk_request(self, request: web.Request) -> web.Response:
        """Redirects a precomp chunk request to the original URL"""
        encoded_original_url = request.match_info.get("encoded_original_url")
        if not encoded_original_url:
            return web.Response(status=400, text="Missing parameter: url")
        info_url = b64decode(encoded_original_url, altchars=b'-_').decode('utf8').lstrip("precomputed://").rstrip("/")
        rest = request.match_info.get("rest", "")
        raise web.HTTPFound(location=f"{info_url}/{rest.lstrip('/')}")



if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--listen-socket", type=Path, required=True)

    subparsers = parser.add_subparsers(required=False, help="tunnel stuff")
    tunnel_parser = subparsers.add_parser("tunnel", help="Creates a reverse tunnel to an orchestrator")
    tunnel_parser.add_argument("--remote-username", type=str, required=True)
    tunnel_parser.add_argument("--remote-host", required=True)
    tunnel_parser.add_argument("--remote-unix-socket", type=Path, required=True)

    args = parser.parse_args()

    mpi_rank = 0
    try:
        from mpi4py import MPI
        mpi_rank = MPI.COMM_WORLD.Get_rank()
    except ModuleNotFoundError:
        pass

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
        WsPixelClassificationWorkflow().run(
            unix_socket_path=str(args.listen_socket)
        )
