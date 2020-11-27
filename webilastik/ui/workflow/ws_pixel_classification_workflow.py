from abc import abstractmethod, ABC
import asyncio
from typing import Optional, Any, Sequence, Dict, List, cast
import typing_extensions
from dataclasses import dataclass
from collections.abc import Mapping as BaseMapping


import json
from webilastik.annotations.annotation import Annotation
import aiohttp
from aiohttp import web
from aiohttp.web import Request

from ndstructs import Slice5D
from ndstructs.utils import JsonSerializable, from_json_data, to_json_data, Dereferencer
from ndstructs.datasource import DataSource

from webilastik.features.ilp_filter import IlpFilter
from webilastik.annotations import Annotation
from webilastik.operator import Operator
from webilastik.ui.applet import Applet, Item_co, SequenceProviderApplet, Slot, CONFIRMER
from webilastik.ui.applet.export_applet import ExportApplet
from webilastik.ui.applet.data_selection_applet import ILane, DataSelectionApplet
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.brushing_applet import BrushingApplet
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet
from webilastik.ui.applet.array5d_viewer import Array5DViewer
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow, PixelClassificationLane
from webilastik.ui.applet.data_selection_applet import url_to_datasource



#FIXME: can we do this without the monkey patching?
@classmethod
#@functools.lru_cache(maxsize=128)
def datasource_from_json_data(cls, data, dereferencer: Dereferencer = None):
    if isinstance(data, str):
        url = data
    elif isinstance(data, BaseMapping):
        url = data["url"]
    else:
        raise ValueError(f"Can't deserialize a datasource from {data}")
    return url_to_datasource(url)
DataSource.from_json_data = datasource_from_json_data

class WsAppletMixin(Applet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.websockets : List[web.WebSocketResponse] = []

    def _get_message_for_remote(self) -> Any:
        return None

    def _update_remote(self):
        async def do_update():
            bad_sockets : List[web.WebSocketResponse] = []
            for websocket in self.websockets:
                try:
                    message = self._get_message_for_remote()
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


class WsSequenceProviderApplet(WsAppletMixin, SequenceProviderApplet[Item_co]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def do_rpc(self, method_name: str, payload: Any):
        if method_name in {'add', 'remove'}:
            items = [self.item_from_json_data(item) for item in payload["items"]]
            return getattr(self, method_name)(items, confirmer=lambda msg: True)
        if method_name in {'clear'}:
            return self.clear(confirmer=lambda msg: True)
        raise Exception(f"Dont know how to run method '{method_name}'")

    @abstractmethod
    def item_from_json_data(self, data: Any) -> Item_co:
        pass

class WsDataSelectionApplet(WsSequenceProviderApplet[PixelClassificationLane], DataSelectionApplet[PixelClassificationLane]):
    def _get_message_for_remote(self):
        print("oooooooooo>>> Updating remote data selection ")
        return {
            "applet_name": "data_selection_applet",#FIXME: maybe have python applets also have names?
            "items": to_json_data(self.items())
        }

    def item_from_json_data(self, data: Any) -> PixelClassificationLane:
        return from_json_data(PixelClassificationLane, data)


class WsBrushingApplet(WsSequenceProviderApplet[Annotation], BrushingApplet):
    def item_from_json_data(self, data: Any) -> Annotation:
        return from_json_data(Annotation.interpolate_from_points, data)


class WsFeatureSelectionApplet(WsSequenceProviderApplet[IlpFilter], FeatureSelectionApplet):
    def item_from_json_data(self, data: Any) -> IlpFilter:
        return IlpFilter.from_json_data(data)


class WsPixelClassificationApplet(WsAppletMixin, PixelClassificationApplet):
    def _get_message_for_remote(self) -> Any:
        classifier = self.pixel_classifier()
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

        data_selection_applet = WsDataSelectionApplet()
        feature_selection_applet = WsFeatureSelectionApplet(lanes=data_selection_applet.items)
        brushing_applet = WsBrushingApplet(lanes=data_selection_applet.items)
        pixel_classifier_applet = WsPixelClassificationApplet(
            lanes=data_selection_applet.items,
            feature_extractors=feature_selection_applet.items,
            annotations=brushing_applet.items,
        )
        predictions_export_applet = ExportApplet(
            lanes=data_selection_applet.items,
            producer=pixel_classifier_applet.pixel_classifier
        )
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
        applet = getattr(self, applet_name)
        if not isinstance(applet, Applet):
            raise Exception(f"Bad applet name: {applet_name}")
        print(f"===>>> Running {applet_name}.{method_name}")
        applet.do_rpc(method_name, args)

    def ng_predict_info(self, request: web.Request):
        lane_index = int(request.match_info.get("lane_index"))
        classifier = self.pixel_classifier_applet.pixel_classifier()
        color_map = self.pixel_classifier_applet.color_map()
        if classifier is None or color_map is None:
            raise ValueError("No classifier trained yet")
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
        lane_index = int(request.match_info.get("lane_index"))
        xBegin = int(request.match_info.get("xBegin"))
        xEnd = int(request.match_info.get("xEnd"))
        yBegin = int(request.match_info.get("yBegin"))
        yEnd = int(request.match_info.get("yEnd"))
        zBegin = int(request.match_info.get("zBegin"))
        zEnd = int(request.match_info.get("zEnd"))

        requested_roi = Slice5D(x=slice(xBegin, xEnd), y=slice(yBegin, yEnd), z=slice(zBegin, zEnd))
        predictions = self.predictions_export_applet.compute_lane(lane_index, slc=requested_roi)

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
    web.get('/wf', workflow.open_websocket),
    web.get(
        "/predictions_export_applet/{uuid}/{lane_index}/data/{xBegin}-{xEnd}_{yBegin}-{yEnd}_{zBegin}-{zEnd}", #uuid so not to cache
        workflow.ng_predict
    ),
    web.get(
        "/predictions_export_applet/{uuid}/{lane_index}/info", #uuid so not to cache
        workflow.ng_predict_info
    ),
    web.post(
        "/ilp_project",
        workflow.ilp_download
    )
])

if __name__ == '__main__':
    web.run_app(app, port=5000)