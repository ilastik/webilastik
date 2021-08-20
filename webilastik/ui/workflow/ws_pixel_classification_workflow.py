from abc import abstractmethod
import sys
import os
import signal
import asyncio
from typing import Iterable, List, Optional, Mapping, Sequence, Set
import json
from base64 import b64decode
import ssl

from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksInfo
from webilastik.utility.url import Url
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonArray, ensureJsonObject, ensureJsonString
from webilastik.scheduling.hashing_executor import HashingExecutor

from webilastik.datasource import DataSource
from webilastik.server.tunnel import ReverseSshTunnel
from pathlib import Path
import contextlib

import aiohttp
from aiohttp import web
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
from webilastik.ui.applet import Applet, Slot
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.brushing_applet import BrushingApplet
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow


def _decode_datasource(datasource_json_b64_altchars_dash_underline: str) -> DataSource:
    json_str = b64decode(datasource_json_b64_altchars_dash_underline.encode('utf8'), altchars=b'-_').decode('utf8')
    return DataSource.from_json_value(json.loads(json_str))


class WsApplet(Applet):
    @abstractmethod
    def _get_json_state(self) -> JsonValue:
        pass

    @abstractmethod
    def _set_json_state(self, state: JsonValue):
        pass

class WsBrushingApplet(WsApplet, BrushingApplet):
    def _get_json_state(self) -> JsonValue:
        return tuple(annotation.to_json_data() for annotation in self.annotations.get() or [])

    def _set_json_state(self, state: JsonValue):
        self.annotations.set_value(
            [Annotation.from_json_value(raw_annotation) for raw_annotation in ensureJsonArray(state)],
            confirmer=lambda msg: True
        )


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
        return tuple(extractor.to_json_data() for extractor in self.feature_extractors.get() or [])

    def _set_json_state(self, state: JsonValue):
        raw_feature_array = ensureJsonArray(state)
        return self.feature_extractors.set_value(
            [self._item_from_json_data(raw_feature) for raw_feature in raw_feature_array],
            confirmer=lambda msg: True
        )


class WsPixelClassificationApplet(WsApplet, PixelClassificationApplet):
    def __init__(
        self,
        name: str,
        *,
        feature_extractors: Slot[Sequence[IlpFilter]],
        annotations: Slot[Sequence[Annotation]],
        runner: HashingExecutor,
    ):
        self.runner = runner
        super().__init__(name=name, feature_extractors=feature_extractors, annotations=annotations)

    def _get_json_state(self) -> JsonValue:
        classifier = self.pixel_classifier.get()
        if classifier:
            producer_is_ready = True
            channel_colors = tuple(color.to_json_data() for color in classifier.color_map.keys())
        else:
            producer_is_ready = False
            channel_colors = tuple()

        return {
            "producer_is_ready": producer_is_ready,
            "channel_colors": channel_colors,
        }

    def _set_json_state(self, state: JsonValue):
        pass

    async def predictions_precomputed_chunks_info(self, request: web.Request):
        classifier = self.pixel_classifier()
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
        predictions = await self.runner.async_submit(
            self.pixel_classifier().compute,
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


class WsPixelClassificationWorkflow(PixelClassificationWorkflow):
    def __init__(self, ssl_context: Optional[ssl.SSLContext] = None):
        self.ssl_context = ssl_context
        self.websockets: List[web.WebSocketResponse] = []
        brushing_applet = WsBrushingApplet("brushing_applet")
        feature_selection_applet = WsFeatureSelectionApplet("feature_selection_applet", datasources=brushing_applet.datasources)
        pixel_classifier_applet = WsPixelClassificationApplet(
            "pixel_classification_applet",
            feature_extractors=feature_selection_applet.feature_extractors,
            annotations=brushing_applet.annotations,
            runner=HashingExecutor(num_workers=8),
        )
        self.wsapplets : Mapping[str, WsApplet] = {
            feature_selection_applet.name: feature_selection_applet,
            brushing_applet.name: brushing_applet,
            pixel_classifier_applet.name: pixel_classifier_applet,
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
        websocket = web.WebSocketResponse()
        await websocket.prepare(request)
        self.websockets.append(websocket)
        await self._update_clients_state([websocket]) # when a new client connects, send it the current state
        async for msg in websocket:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close':
                    await websocket.close()
                    continue
                try:
                    payload = json.loads(msg.data)
                    await self._update_local_state(new_state=payload, originator=websocket)
                except Exception as e:
                    print(f"Exception happened on set state:\n\033[31m{e}\033[0m")
                    import traceback
                    traceback.print_exc()
                    await self._update_clients_state([websocket]) # restore last known good state of offending client
            elif msg.type == aiohttp.WSMsgType.BINARY:
                print(f'Unexpected binary message')
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(f'ws connection closed with exception {websocket.exception()}')
        if websocket in self.websockets:
            self.websockets.remove(websocket)
        print('websocket connection closed')
        return websocket

    async def _update_local_state(self, new_state: JsonValue, originator: web.WebSocketResponse):
        print(f"\033[34m Got new state:\n{json.dumps(new_state, indent=4)}\n \033[0m")
        state_obj = ensureJsonObject(new_state)
        # FIXME: sort applets maybe? only allow for a single applet update?
        updated_wsapplets: Set[WsApplet] = set()
        for applet_name, raw_applet_state in state_obj.items():
            wsapplet = self.wsapplets[applet_name]
            wsapplet._set_json_state(raw_applet_state)
            updated_wsapplets.update([wsapplet])
            updated_wsapplets.update([ap for ap in wsapplet.get_downstream_applets() if isinstance(ap, WsApplet)])

        updated_state = {applet.name: applet._get_json_state() for applet in updated_wsapplets}
        originator_updated_state = {key: value for key, value in updated_state.items() if key not in state_obj} # FIXME

        for websocket in self.websockets:
            try:
                if websocket == originator:
                    await websocket.send_str(json.dumps(originator_updated_state))
                else:
                    await websocket.send_str(json.dumps(updated_state))
            except ConnectionResetError as e:
                print(f"!!!!!+++!!!! Got an exception while updating remote:\n{e}\n\nRemoving websocket...")
                self.websockets.remove(websocket)

    async def _update_clients_state(self, websockets: Iterable[web.WebSocketResponse] = ()):
        state : JsonObject = {applet.name: applet._get_json_state() for applet in self.wsapplets.values()}
        print(f"\033[32m  Updating remote to following state:\n{json.dumps(state, indent=4)}  \033[0m")
        for websocket in list(websockets):
            try:
                await websocket.send_str(json.dumps(state))
            except ConnectionResetError as e:
                print(f"!!!!!+++!!!! Got an exception while updating remote:\n{e}\n\nRemoving websocket...")
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
        print(f"+++++ Will request this info: {info_url.schemeless_raw}", file=sys.stderr)
        async with aiohttp.ClientSession() as session:
            async with session.get(info_url.schemeless_raw, ssl=self.ssl_context) as response:
                response_text = await response.text()
                if response.status // 100 != 2:
                    return web.Response(status=response.status, text=response_text)
                info = PrecomputedChunksInfo.from_json_data(json.loads(response_text))

        stripped_info = info.stripped(resolution=resolution)
        return web.json_response(stripped_info.to_json_data())

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
            print(f"File not found: {ca_crt}", file=sys.stderr)
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
        WsPixelClassificationWorkflow(ssl_context=ssl_context).run(
            unix_socket_path=str(args.listen_socket)
        )
