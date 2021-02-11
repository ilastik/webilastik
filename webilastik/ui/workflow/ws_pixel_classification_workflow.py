from abc import abstractmethod, ABC
import asyncio
from typing import Any, Dict, List, cast, Mapping
from collections.abc import Mapping as BaseMapping
import json

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
from webilastik.ui.applet.sequence_provider_applet import SequenceProviderApplet, Item_co
from webilastik.ui.applet.export_applet import ExportApplet
from webilastik.ui.applet.data_selection_applet import DataSelectionApplet
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.brushing_applet import BrushingApplet
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow, PixelClassificationLane


class WsAppletMixin(Applet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.websockets : List[web.WebSocketResponse] = []

    def _get_status_message(self) -> JSON_VALUE:
        return None

    def _update_remote(self):
        async def do_update():
            bad_sockets : List[web.WebSocketResponse] = []
            for websocket in self.websockets:
                try:
                    message = self._get_status_message()
                    if message is not None:
                        await websocket.send_str(json.dumps(message))
                except ConnectionResetError as e:
                    print(f"Got an exception while updating remote. Removing websocket...")
                    bad_sockets.append(websocket)
            for bad_socket in bad_sockets:
                self.websockets.remove(bad_socket)
        asyncio.get_event_loop().create_task(do_update())

    def _add_websocket(self, websocket: web.WebSocketResponse):
        self.websockets.append(websocket)

    def post_refresh(self, confirmer: CONFIRMER): #FIXME: this will fire even if something breaks downstream
        super().post_refresh(confirmer)
        self._update_remote()

    def restore_snaphot(self, snap: Dict[str, Any]):
        super().restore_snaphot(snap)
        self._update_remote()

    @abstractmethod
    def do_rpc(self, method_name: str, payload: Any):
        pass


class WsSequenceProviderApplet(WsAppletMixin, SequenceProviderApplet[Item_co]):
    def do_rpc(self, method_name: str, payload: Any):
        if method_name in {'add', 'remove'}:
            items = [self.item_from_json_data(item) for item in payload["items"]]
            return getattr(self, method_name)(items, confirmer=lambda msg: True)
        if method_name in {'clear'}:
            return self.clear(confirmer=lambda msg: True)
        raise Exception(f"Dont know how to run method '{method_name}'")

    @abstractmethod
    def item_from_json_data(self, data: JSON_VALUE) -> Item_co:
        pass

class WsDataSelectionApplet(WsSequenceProviderApplet[PixelClassificationLane], DataSelectionApplet[PixelClassificationLane]):
    def _get_status_message(self) -> JSON_VALUE:
        return {
            "applet_name": self.name,#FIXME: maybe have python applets also have names?
            "items": [item.to_json_data() for item in self.items()]
        }

    def item_from_json_data(self, data: JSON_VALUE) -> PixelClassificationLane:
        return PixelClassificationLane.from_json_data(data)


class WsBrushingApplet(WsSequenceProviderApplet[Annotation], BrushingApplet[PixelClassificationLane]):
    def item_from_json_data(self, data: JSON_VALUE) -> Annotation:
        return Annotation.from_json_data(data)


class WsFeatureSelectionApplet(WsSequenceProviderApplet[IlpFilter], FeatureSelectionApplet):
    def item_from_json_data(self, data: JSON_VALUE) -> IlpFilter:
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


class WsPixelClassificationApplet(WsAppletMixin, PixelClassificationApplet[PixelClassificationLane]):
    def do_rpc(self, method_name: str, payload: Any):
        raise NotImplementedError

    def _get_status_message(self) -> Any:
        classifier = self.pixel_classifier.get()
        if classifier is None:
            return None

        color_lines: List[str] = []
        colors_to_mix: List[str] = []

        for idx, color in enumerate(classifier.color_map.keys()):
            color_line = (
                f"vec3 color{idx} = (vec3({color.r}, {color.g}, {color.b}) / 255.0) * toNormalized(getDataValue({idx}));"
            )
            color_lines.append(color_line)
            colors_to_mix.append(f"color{idx}")

        shader_lines = [
            "void main() {",
            "    " + "\n    ".join(color_lines),
            "    emitRGBA(",
           f"        vec4({' + '.join(colors_to_mix)}, 1.0)",
            "    );",
            "}",
        ]
        shader = "\n".join(shader_lines)

        return {
            "applet_name": "pixel_classifier_applet",#FIXME: maybe have python applets also have names?
            "predictions_shader": shader
        }


class WsPixelClassificationWorkflow(PixelClassificationWorkflow):
    def __init__(self, websockets: List[web.WebSocketResponse]):
        self.app = web.Application()

        data_selection_applet = WsDataSelectionApplet("data_selection_applet")
        feature_selection_applet = WsFeatureSelectionApplet("feature_selection_applet", lanes=data_selection_applet.items)
        brushing_applet = WsBrushingApplet("brushing_applet", lanes=data_selection_applet.items)
        pixel_classifier_applet = WsPixelClassificationApplet(
            "pixel_classifier_applet",
            lanes=data_selection_applet.items,
            feature_extractors=feature_selection_applet.items,
            annotations=brushing_applet.items,
        )
        predictions_export_applet = ExportApplet(
            "predictions_export_applet",
            lanes=data_selection_applet.items,
            producer=pixel_classifier_applet.pixel_classifier
        )
        self.applets : Mapping[str, WsAppletMixin] = {
            aplt.name : aplt for aplt in (data_selection_applet, feature_selection_applet, brushing_applet, pixel_classifier_applet)
        }
        super().__init__(
            data_selection_applet=data_selection_applet,
            feature_selection_applet=feature_selection_applet,
            brushing_applet=brushing_applet,
            pixel_classifier_applet=pixel_classifier_applet,
            predictions_export_applet=predictions_export_applet
        )
        self.websockets : List[web.WebSocketResponse] = []
        for ws in websockets:
            self._add_websocket(ws)

    def _add_websocket(self, websocket: web.WebSocketResponse):
        self.websockets.append(websocket)
        for applet in [app for app in self.__dict__.values() if isinstance(app, WsAppletMixin)]:
            applet._add_websocket(websocket)

    async def open_websocket(self, request: web.Request):
        websocket = web.WebSocketResponse() #FIXME: what happens on 2 connections?
        await websocket.prepare(request)
        self._add_websocket(websocket)

        async for msg in websocket:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close':
                    await websocket.close()
                else:
                    workflow.run_rpc(msg.data)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(f'ws connection closed with exception {websocket.exception()}')
        self.websockets.remove(websocket)
        print('websocket connection closed')

    def run_rpc(self, payload: str):
        rpc_request = json.loads(payload)
        applet_name = rpc_request["applet_name"]
        method_name = rpc_request["method_name"]
        args = rpc_request.get("args", {})
        applet = self.applets.get(applet_name)
        if applet == None:
            raise Exception(f"Bad applet name: {applet_name}")
        print(f"===>>> Running {applet_name}.{method_name} with args {args}")
        applet.do_rpc(method_name, args)

    def ng_predict_info(self, request: web.Request):
        lane_index = int(request.match_info.get("lane_index"))  # type: ignore
        classifier = self.pixel_classifier_applet.pixel_classifier()
        color_map = self.pixel_classifier_applet.color_map()
        expected_num_channels = len(color_map)
        datasource = self.data_selection_applet.items()[lane_index].get_raw_data()

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
            headers={"Access-Control-Allow-Origin": "*"})

    def ng_predict(self, request: web.Request):
        lane_index = int(request.match_info.get("lane_index")) # type: ignore
        xBegin = int(request.match_info.get("xBegin")) # type: ignore
        xEnd = int(request.match_info.get("xEnd")) # type: ignore
        yBegin = int(request.match_info.get("yBegin")) # type: ignore
        yEnd = int(request.match_info.get("yEnd")) # type: ignore
        zBegin = int(request.match_info.get("zBegin")) # type: ignore
        zEnd = int(request.match_info.get("zEnd")) # type: ignore

        datasource = self.data_selection_applet.items()[lane_index]
        predictions = self.predictions_export_applet.compute(
            DataRoi(datasource.get_raw_data(), x=(xBegin, xEnd), y=(yBegin, yEnd), z=(zBegin, zEnd))
        )

        # https://github.com/google/neuroglancer/tree/master/src/neuroglancer/datasource/precomputed#raw-chunk-encoding
        # "(...) data for the chunk is stored directly in little-endian binary format in [x, y, z, channel] Fortran order"
        resp = predictions.as_uint8().raw("xyzc").tobytes("F")
        return web.Response(
            body=resp,
            content_type="application/octet-stream",
            headers={"Access-Control-Allow-Origin": "*"}
        )

    def ilp_download(self, request: web.Request):
        return web.Response(
            body=self.ilp_file.read(),
            content_type="application/octet-stream",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Content-disposition": 'attachment; filename="MyProject.ilp"'
            }
        )

workflow = WsPixelClassificationWorkflow(websockets=[])

app = web.Application()
app.add_routes([
    web.get('/wf', workflow.open_websocket), # type: ignore
    web.get(
        "/predictions_export_applet/{uuid}/{lane_index}/data/{xBegin}-{xEnd}_{yBegin}-{yEnd}_{zBegin}-{zEnd}", #FIXME uuid is just there to prevent caching
        workflow.ng_predict # type: ignore
    ),
    web.get(
        "/predictions_export_applet/{uuid}/{lane_index}/info", #FIXME uuid is just there to prevent caching
        workflow.ng_predict_info # type: ignore
    ),
    web.post(
        "/ilp_project",
        workflow.ilp_download # type: ignore
    )
])

if __name__ == '__main__':
    web.run_app(app, port=5000)
