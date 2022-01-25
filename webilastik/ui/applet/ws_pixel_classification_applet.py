from typing import Optional, Sequence
from base64 import b64decode
import asyncio
import json

from ndstructs.utils.json_serializable import JsonObject, JsonValue
from aiohttp import web

from webilastik.annotations.annotation import Annotation
from webilastik.datasource import DataRoi, DataSource
from webilastik.features.ilp_filter import IlpFilter
from webilastik.scheduling.hashing_executor import HashingExecutor
from webilastik.ui.applet import AppletOutput, UserPrompt
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError

def _decode_datasource(datasource_json_b64_altchars_dash_underline: str) -> DataSource:
    json_str = b64decode(datasource_json_b64_altchars_dash_underline.encode('utf8'), altchars=b'-_').decode('utf8')
    return DataSource.from_json_value(json.loads(json_str))

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
            "classifier_generation": self.classifier_generation,
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
