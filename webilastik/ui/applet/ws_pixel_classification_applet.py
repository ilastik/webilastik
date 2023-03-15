from pathlib import PurePosixPath
from typing import Optional, List
import asyncio

import numpy as np
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonBoolean
from aiohttp import web
from webilastik.classifiers.pixel_classifier import PixelClassifier, VigraPixelClassifier

from webilastik.datasource import DataRoi, FsDataSource
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksInfo, PrecomputedChunksScale, RawEncoder
from webilastik.server.util import get_encoded_datasource_from_url
from webilastik.server.rpc import MessageParsingError
from webilastik.server.rpc.dto import CheckDatasourceCompatibilityParams, CheckDatasourceCompatibilityResponse, RpcErrorDto, Shape5DDto
from webilastik.ui.applet import CascadeError, UserPrompt
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError
from webilastik.server.session_allocator import uncachable_json_response

class WsPixelClassificationApplet(WsApplet, PixelClassificationApplet):
    def _get_json_state(self) -> JsonValue:
        with self.lock:
            state = self._state
            label_classes = self._in_label_classes()

        minInputShape: Optional[Shape5DDto] = None
        if isinstance(state.classifier, VigraPixelClassifier):
            minInputShape = Shape5DDto.from_shape5d(state.classifier.minInputShape)

        return {
            "generation": state.generation,
            "description": state.description,
            "live_update": state.live_update,
            # vigra will output only as many channels as number of values in the samples, so empty labels are a problem
            "channel_colors": tuple(color.to_dto().to_json_value() for color, annotations in label_classes.items() if len(annotations) > 0),
            "minInputShape": None if minInputShape is None else minInputShape.to_json_value(),
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

        ds_result = get_encoded_datasource_from_url(match_info_key="encoded_raw_data", request=request)
        if isinstance(ds_result, Exception):
            return uncachable_json_response(payload=f"Could not get data source from URL: {ds_result}", status=400)

        info = PrecomputedChunksInfo(
            type_="image",
            data_type=np.dtype("uint8"), #FIXME: use float, fix display in shader
            num_channels=classifier.num_classes,
            scales=tuple([
                PrecomputedChunksScale(
                    chunk_sizes=tuple([
                        (ds_result.tile_shape.x, ds_result.tile_shape.y, ds_result.tile_shape.z)
                    ]),
                    encoding=RawEncoder(),
                    key=PurePosixPath("data"),
                    resolution=ds_result.spatial_resolution,
                    size=(ds_result.shape.x, ds_result.shape.y, ds_result.shape.z),
                    voxel_offset=(ds_result.interval.start.x, ds_result.interval.start.y, ds_result.interval.start.z),
                )
            ])
        )

        return uncachable_json_response(info.to_json_value(), status=200)

    async def precomputed_chunks_compute(self, request: web.Request) -> web.Response:
        generation = int(request.match_info.get("generation")) # type: ignore
        xBegin = int(request.match_info.get("xBegin")) # type: ignore
        xEnd = int(request.match_info.get("xEnd")) # type: ignore
        yBegin = int(request.match_info.get("yBegin")) # type: ignore
        yEnd = int(request.match_info.get("yEnd")) # type: ignore
        zBegin = int(request.match_info.get("zBegin")) # type: ignore
        zEnd = int(request.match_info.get("zEnd")) # type: ignore

        ds_result = get_encoded_datasource_from_url(match_info_key="encoded_raw_data", request=request)
        if isinstance(ds_result, Exception):
            return uncachable_json_response(payload=f"Could not get data source from URL: {ds_result}", status=400)
        datasource = ds_result

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
