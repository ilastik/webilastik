from typing import Optional, Tuple, Union
from pathlib import Path, PurePosixPath
from dataclasses import dataclass

from numpy import dtype

from ndstructs.point5D import Shape5D
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonIntTripplet, ensureJsonString, ensureOptional, toJsonValue
from webilastik.datasource import DataSource
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksEncoder, PrecomputedChunksInfo, PrecomputedChunksScale, RawEncoder
from webilastik.libebrains.user_token import UserToken
from webilastik.ui import parse_url

from webilastik.ui.applet import Applet, AppletOutput, InertApplet, PropagationError, PropagationOk, PropagationResult, UserPrompt, applet_output, user_interaction
from webilastik.datasink import DataSink
from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksSink
from webilastik.filesystem.bucket_fs import BucketFs
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError
from webilastik.utility import get_now_string

@dataclass
class State:
    sink: Optional[DataSink]

class DataSinkSelectorApplet(InertApplet):
    def __init__(
        self,
        *,
        name: str,
        ebrains_user_token: UserToken,
        shape: AppletOutput[Optional[Shape5D]],
        tile_shape: AppletOutput[Optional[Shape5D]],
        spatial_resolution: AppletOutput[Optional[Tuple[int, int, int]]],
        num_channels_override: Optional[AppletOutput[Optional[int]]] = None,
    ) -> None:
        self.ebrains_user_token = ebrains_user_token
        self._in_shape = shape
        self._in_tile_shape = tile_shape
        self._in_spatial_resolution = spatial_resolution
        self._in_num_channels_override = num_channels_override

        self._bucket_name: Optional[str] = "hbp-image-service"
        self._prefix: Optional[PurePosixPath] = PurePosixPath(f"/webilastik_job_{get_now_string()}.precomputed")
        self._voxel_offset: Tuple[int, int, int] = (0,0,0)
        self._encoder: PrecomputedChunksEncoder = RawEncoder()
        self._datasink: Optional[DataSink] = None
        super().__init__(name)

    def take_snapshot(self) -> State:
        return State(sink=self._datasink) # FIXME: double check this

    def restore_snaphot(self, snapshot: State) -> None:
        self._datasink = snapshot.sink

    @user_interaction
    def set_params(
        self,
        user_prompt: UserPrompt,
        bucket_name: Optional[str] = None,
        prefix: Optional[PurePosixPath] = None,
        voxel_offset: Optional[Tuple[int, int, int]] = None,
        encoder: Optional[PrecomputedChunksEncoder] = RawEncoder(),
    ) -> PropagationResult:
        self._bucket_name = bucket_name
        self._prefix = prefix
        self._voxel_offset = voxel_offset or (0, 0, 0)
        self._encoder = encoder or RawEncoder()
        return PropagationOk()

    @applet_output
    def datasink(self) -> Union[DataSink, UsageError, None]:
        shape = self._in_shape()
        tile_shape = self._in_tile_shape()
        spatial_resolution = self._in_spatial_resolution()

        if (
            shape is None or
            tile_shape is None or
            spatial_resolution is None or
            self._bucket_name is None or
            self._prefix is None or
            self._encoder is None
        ):
            return None

        num_channels = (self._in_num_channels_override and self._in_num_channels_override()) or shape.c
        shape = shape.updated(c=num_channels)
        try:
            print(f"++++++++++++ trying to generate a data sink.....")
            filesystem = BucketFs(
                bucket_name=self._bucket_name,
                prefix=PurePosixPath(self._prefix),
                ebrains_user_token=self.ebrains_user_token,
            )
            sink = PrecomputedChunksSink.create(
                base_path=Path(self._prefix), #FIXME
                filesystem=filesystem,
                info=PrecomputedChunksInfo(
                    data_type=dtype("float32"), #FIXME? maybe operator.expected_dtype or smth?
                    type_="image",
                    num_channels=shape.c,
                    scales=tuple([
                        PrecomputedChunksScale(
                            key=Path("exported_data"),
                            size=(shape.x, shape.y, shape.z),
                            chunk_sizes=( (tile_shape.x, tile_shape.y, tile_shape.z), ),
                            encoding=self._encoder,
                            voxel_offset=self._voxel_offset,
                            resolution=spatial_resolution
                        )
                    ]),
                )
            ).scale_sinks[0]
            return sink
        except Exception as e:
            import traceback
            print(f"++++++++++++++ Could not create a datasink: {e}")
            traceback.print_exc()
            return UsageError(str(e))

class WsDataSinkSelectorApplet(WsApplet, DataSinkSelectorApplet):
    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        if method_name == "set_params":
            bucket_name = ensureOptional(ensureJsonString, arguments.get("bucket_name"))
            prefix = ensureOptional(ensureJsonString, arguments.get("prefix"))
            voxel_offset = ensureOptional(ensureJsonIntTripplet, arguments.get("voxel_offset"))
            encoder = ensureOptional(PrecomputedChunksEncoder.from_json_value, arguments.get("encoder"))
            rpc_result = self.set_params(
                user_prompt=user_prompt,
                bucket_name=bucket_name,
                prefix=PurePosixPath(prefix) if prefix else None,
                voxel_offset=voxel_offset,
                encoder=encoder,
            )
            if isinstance(rpc_result, PropagationError):
                return UsageError(rpc_result.message)
            return

        return UsageError(f"Method not found: {method_name}")

    def _get_json_state(self) -> JsonValue:
        return {
            "bucket_name": toJsonValue(self._bucket_name),
            "prefix": toJsonValue(self._prefix and str(self._prefix)),
            "voxel_offset": toJsonValue(self._voxel_offset),
            "encoder": toJsonValue(self._encoder),
        }