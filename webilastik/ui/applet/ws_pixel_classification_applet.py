from typing import Optional, List
from base64 import b64decode
import asyncio
import json

from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonBoolean
from aiohttp import web
from webilastik import datasource
from webilastik.classifiers.pixel_classifier import PixelClassifier

from webilastik.datasource import DataRoi, FsDataSource
from webilastik.server.rpc import MessageParsingError
from webilastik.server.rpc.dto import CheckDatasourceCompatibilityParams, CheckDatasourceCompatibilityResponse, RpcErrorDto
from webilastik.ui.applet import CascadeError, UserPrompt
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.datasource import try_get_datasources_from_url
from webilastik.ui.usage_error import UsageError
from webilastik.utility.url import Protocol, Url
from webilastik.server.session_allocator import uncachable_json_response


def _decode_datasource_url(encoded_url: str) -> "FsDataSource | web.Response":
    try:
        datasource_url = Url.from_base64(encoded_url)
    except Exception:
        return uncachable_json_response({"error": f"Bad raw_data encoded url: {encoded_url}"}, status=400)
    datasources_result = try_get_datasources_from_url(url=datasource_url)
    if isinstance(datasources_result, Exception):
        return uncachable_json_response({"error": f"Could not open datasource at {datasource_url}"}, status=500)
    if isinstance(datasources_result, type(None)):
        return uncachable_json_response({"error": f"Unsupported datasource at {datasource_url}"}, status=400)
    if len(datasources_result) != 1:
        return uncachable_json_response({"error": f"Expect url to lead to one single datasource: {datasource_url}"}, status=400)
    return datasources_result[0]


class WsPixelClassificationApplet(WsApplet, PixelClassificationApplet):
    def _get_json_state(self) -> JsonValue:
        with self.lock:
            state = self._state
            label_classes = self._in_label_classes()

        return {
            "generation": state.generation,
            "description": state.description,
            "live_update": state.live_update,
            # vigra will output only as many channels as number of values in the samples, so empty labels are a problem
            "channel_colors": tuple(color.to_dto().to_json_value() for color, annotations in label_classes.items() if len(annotations) > 0),
        }

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        if(method_name == "set_live_update"):
            live_update = ensureJsonBoolean(arguments.get("live_update"))
            result = self.set_live_update(user_prompt=user_prompt, live_update=live_update)
            if isinstance(result, CascadeError):
                return UsageError(result.message)
            return None

        raise ValueError(f"Invalid method name: '{method_name}'")

    async def check_datasource_compatibility(self, request: web.Request) -> web.Response:
        params = CheckDatasourceCompatibilityParams.from_json_value(await request.json())
        if isinstance(params, MessageParsingError):
            return  uncachable_json_response(RpcErrorDto(error="bad payload").to_json_value(), status=400)
        datasources: List[FsDataSource] = []
        for dto in params.datasources:
            ds = FsDataSource.try_from_message(dto)
            if isinstance(ds, Exception):
                return uncachable_json_response(RpcErrorDto(error=str(ds)).to_json_value(), status=400)
            datasources.append(ds)
        with self.lock:
            classifier = self.pixel_classifier()
        if classifier is None:
            return uncachable_json_response("Request is for stale classifier", status=410)
        return uncachable_json_response(
            CheckDatasourceCompatibilityResponse(
                compatible=tuple(classifier.is_applicable_to(ds) for ds in datasources)
            ).to_json_value(),
            status=200,
        )

    async def predictions_precomputed_chunks_info(self, request: web.Request) -> web.Response:
        classifier = self._state.classifier
        if not isinstance(classifier, PixelClassifier) :
            return web.json_response({"error": "Classifier is not ready yet"}, status=412)

        encoded_raw_data_url = str(request.match_info.get("encoded_raw_data_url"))
        datasource_result = _decode_datasource_url(encoded_raw_data_url)
        if not isinstance(datasource_result, FsDataSource):
            return datasource_result
        datasource = datasource_result

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
        encoded_raw_data_url = str(request.match_info.get("encoded_raw_data_url"))
        generation = int(request.match_info.get("generation")) # type: ignore
        xBegin = int(request.match_info.get("xBegin")) # type: ignore
        xEnd = int(request.match_info.get("xEnd")) # type: ignore
        yBegin = int(request.match_info.get("yBegin")) # type: ignore
        yEnd = int(request.match_info.get("yEnd")) # type: ignore
        zBegin = int(request.match_info.get("zBegin")) # type: ignore
        zEnd = int(request.match_info.get("zEnd")) # type: ignore

        datasource_result = _decode_datasource_url(encoded_raw_data_url)
        if not isinstance(datasource_result, FsDataSource):
            return datasource_result
        datasource = datasource_result

        with self.lock:
            classifier = self.pixel_classifier()
            label_classes = self._in_label_classes()
        if classifier is None:
            return web.json_response({"error": "Classifier is not ready yet"}, status=412)

        if generation != self._state.generation:
            return web.json_response({"error": "This classifier is stale"}, status=410)

        predictions = await asyncio.wrap_future(self.executor.submit(
            classifier,
            DataRoi(datasource, x=(xBegin, xEnd), y=(yBegin, yEnd), z=(zBegin, zEnd))
        ))

        if "format" in request.query:
            requested_format = request.query["format"]
            if requested_format != "png":
                return web.Response(status=400, text=f"Server-side rendering only available in png, not in {requested_format}")
            if predictions.shape.z > 1:
                return web.Response(status=400, text="Server-side rendering only available for 2d images")

            class_colors = tuple(label_classes.keys())
            prediction_png_bytes = list(predictions.to_z_slice_pngs(class_colors))[0] #FIXME assumes shape.t=1 and shape.z=1
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
