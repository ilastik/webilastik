from abc import abstractmethod, ABC
import os
import signal
import asyncio
from typing import Any, Dict, List, Optional, Mapping, cast
import json
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
from webilastik.utility.serialization import ValueGetter, JSON_VALUE
from webilastik.annotations.annotation import Annotation
from webilastik.features.ilp_filter import IlpFilter
from webilastik.annotations import Annotation
from webilastik.ui.applet import Applet, CONFIRMER
from webilastik.ui.applet.export_applet import ExportApplet
from webilastik.ui.applet.data_selection_applet import DataSelectionApplet
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.brushing_applet import BrushingApplet
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow, PixelClassificationLane

class WsAppletMixin(Applet):
    @property
    def websockets(self) -> List[web.WebSocketResponse]:
        if not hasattr(self,"_websockets"):
            self._websockets = cast(List[web.WebSocketResponse], [])
        return self._websockets

    @abstractmethod
    def _get_json_state(self) -> JSON_VALUE:
        pass

    @abstractmethod
    def _set_json_state(self, state: JSON_VALUE):
        pass

    async def _update_remote(self):
        bad_sockets : List[web.WebSocketResponse] = []
        for websocket in self.websockets:
            try:
                state = self._get_json_state()
                if state is not None:
                    await websocket.send_str(json.dumps(state))
            except ConnectionResetError as e:
                print(f"Got an exception while updating remote:\n{e}\n\nRemoving websocket...")
                bad_sockets.append(websocket)
        for bad_socket in bad_sockets:
            self.websockets.remove(bad_socket)

    async def _add_websocket(self, websocket: web.WebSocketResponse):
        self.websockets.append(websocket)
        async for msg in websocket:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close':
                    await websocket.close()
                else:
                    payload = json.loads(msg.data)
                    method_name = ValueGetter(str).get(key="method_name", data=payload)
                    if method_name == "set_state":
                        self._set_json_state(payload["state"])
                    elif method_name == "get_state":
                        await self._update_remote()
                    else:
                        raise ValueError(f"Bad method_name in socket communication: {method_name}")
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


class WsDataSelectionApplet(WsAppletMixin, DataSelectionApplet[PixelClassificationLane]):
    def _get_json_state(self) -> JSON_VALUE:
        return [lane.to_json_data() for lane in self.lanes.get(default=[])]

    def _set_json_state(self, state: JSON_VALUE):
        if not isinstance(state, list):
            raise TypeError(f"Bad state value in {self.__class__.__name__}:\n", json.dumps(state))
        return self.lanes.set_value(
            [PixelClassificationLane.from_json_data(raw_lane) for raw_lane in state],
            confirmer=lambda msg: True
        )


class WsBrushingApplet(WsAppletMixin, BrushingApplet[PixelClassificationLane]):
    def _get_json_state(self) -> JSON_VALUE:
        return [annotation.to_json_data() for annotation in self.annotations.get(default=[])]

    def _set_json_state(self, state: JSON_VALUE):
        if not isinstance(state, list):
            raise TypeError(f"Bad state value in {self.__class__.__name__}:\n", json.dumps(state))
        return self.annotations.set_value(
            [Annotation.from_json_data(raw_lane) for raw_lane in state],
            confirmer=lambda msg: True
        )


class WsFeatureSelectionApplet(WsAppletMixin, FeatureSelectionApplet):
    def _item_from_json_data(self, data: JSON_VALUE) -> IlpFilter:
        class_name = ValueGetter.get_class_name(data=data)
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

    def _get_json_state(self) -> JSON_VALUE:
        return [extractor.to_json_data() for extractor in self.feature_extractors.get(default=[])]

    def _set_json_state(self, state: JSON_VALUE):
        if not isinstance(state, list):
            raise TypeError(f"Bad state value in {self.__class__.__name__}:\n", json.dumps(state))
        return self.feature_extractors.set_value(
            [self._item_from_json_data(raw_lane) for raw_lane in state],
            confirmer=lambda msg: True
        )


class WsPixelClassificationWorkflow(PixelClassificationWorkflow):
    def __init__(self):
        data_selection_applet = WsDataSelectionApplet("data_selection_applet")
        feature_selection_applet = WsFeatureSelectionApplet("feature_selection_applet", lanes=data_selection_applet.lanes)
        brushing_applet = WsBrushingApplet("brushing_applet", lanes=data_selection_applet.lanes)
        pixel_classifier_applet = PixelClassificationApplet(
            "pixel_classifier_applet",
            lanes=data_selection_applet.lanes,
            feature_extractors=feature_selection_applet.feature_extractors,
            annotations=brushing_applet.annotations,
        )
        predictions_export_applet = ExportApplet(
            "predictions_export_applet",
            lanes=data_selection_applet.lanes,
            producer=pixel_classifier_applet.pixel_classifier
        )
        self.ws_applets : Mapping[str, WsAppletMixin] = {
            data_selection_applet.name: data_selection_applet,
            feature_selection_applet.name: feature_selection_applet,
            brushing_applet.name: brushing_applet
        }
        super().__init__(
            data_selection_applet=data_selection_applet,
            feature_selection_applet=feature_selection_applet,
            brushing_applet=brushing_applet,
            pixel_classifier_applet=pixel_classifier_applet,
            predictions_export_applet=predictions_export_applet
        )

        self.app = web.Application()
        self.app.add_routes([
            web.get('/ws/{applet_name}', self.open_websocket), # type: ignore
            web.get(
                "/predictions_export_applet/{uuid}/{lane_index}/data/{xBegin}-{xEnd}_{yBegin}-{yEnd}_{zBegin}-{zEnd}", #FIXME uuid is just there to prevent caching
                self.ng_predict
            ),
            web.get(
                "/predictions_export_applet/{uuid}/{lane_index}/info", #FIXME uuid is just there to prevent caching
                self.ng_predict_info
            ),
            web.post("/ilp_project", self.ilp_download),
            web.delete("/close", self.close_session),
        ])

    async def close_session(self, request: web.Request) -> web.Response:
        asyncio.create_task(self._self_destruct(delay=5))
        return web.Response()

    async def _self_destruct(self, delay: int):
        #FIXME: is there a clean way to close the server? self.app.(shutdown|cleanup) are not it
        await asyncio.sleep(delay)
        os.kill(os.getpid(), signal.SIGINT)

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

    async def ng_predict_info(self, request: web.Request):
        lane_index = int(request.match_info.get("lane_index"))  # type: ignore
        classifier = self.pixel_classifier_applet.pixel_classifier()
        color_map = self.pixel_classifier_applet.color_map()
        expected_num_channels = len(color_map)
        datasource = self.data_selection_applet.lanes()[lane_index].get_raw_data()

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
            content_type="application/json",
        )

    async def ng_predict(self, request: web.Request):
        lane_index = int(request.match_info.get("lane_index")) # type: ignore
        xBegin = int(request.match_info.get("xBegin")) # type: ignore
        xEnd = int(request.match_info.get("xEnd")) # type: ignore
        yBegin = int(request.match_info.get("yBegin")) # type: ignore
        yEnd = int(request.match_info.get("yEnd")) # type: ignore
        zBegin = int(request.match_info.get("zBegin")) # type: ignore
        zEnd = int(request.match_info.get("zEnd")) # type: ignore

        datasource = self.data_selection_applet.lanes()[lane_index]
        predictions = await self.predictions_export_applet.async_compute(
            DataRoi(datasource.get_raw_data(), x=(xBegin, xEnd), y=(yBegin, yEnd), z=(zBegin, zEnd))
        )

        # https://github.com/google/neuroglancer/tree/master/src/neuroglancer/datasource/precomputed#raw-chunk-encoding
        # "(...) data for the chunk is stored directly in little-endian binary format in [x, y, z, channel] Fortran order"
        resp = predictions.as_uint8().raw("xyzc").tobytes("F")
        return web.Response(
            body=resp,
            content_type="application/octet-stream",
        )

    async def ilp_download(self, request: web.Request):
        return web.Response(
            body=self.ilp_file.read(),
            content_type="application/octet-stream",
            headers={
                "Content-disposition": 'attachment; filename="MyProject.ilp"'
            }
        )

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
