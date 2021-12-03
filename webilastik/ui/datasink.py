# pyright: strict

from abc import abstractmethod
from pathlib import Path
from typing import ClassVar, Dict, Optional, Sequence, Tuple, Type, TypeVar, Union
from dataclasses import dataclass
# import functools

import numpy as np
from ndstructs.point5D import Interval5D, Point5D, Shape5D
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString
from webilastik.datasink import DataSink
from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksSink

from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksEncoder, PrecomputedChunksInfo, PrecomputedChunksScale, RawEncoder
from webilastik.libebrains.user_token import UserToken
from webilastik.ui.filesystem import try_filesystem_from_url
from webilastik.ui.usage_error import UsageError

from webilastik.utility.url import Url, Protocol

DT = TypeVar("DT", np.uint8, np.float32)

@dataclass
class DataSinkCreationParams:
    registry: ClassVar[Dict[str, Type["DataSinkCreationParams"]]] = {}

    def __init__(self, url: Url) -> None:
        self.url = url

    def __init_subclass__(cls) -> None:
        DataSinkCreationParams.registry[cls.__name__] = cls

    @classmethod
    @abstractmethod
    def from_json_value(cls, value: JsonValue) -> "DataSinkCreationParams":
        value_obj = ensureJsonObject(value)
        marker = ensureJsonString(value_obj.get("__class__"))
        a = DataSinkCreationParams.registry[marker].from_json_value(value)
        return a


    @abstractmethod
    def try_load(
        self,
        *,
        ebrains_user_token: Optional[UserToken],
        allowed_protocols: Sequence[Protocol] = (Protocol.HTTP, Protocol.HTTPS),
        dtype: "np.dtype[DT]",
        interval: Interval5D,
        chunk_size: Shape5D,
        location: Point5D,
        spatial_resolution: Tuple[int, int, int],
    ) -> Union[DataSink, UsageError]:
        raise NotImplementedError

class PrecomputedChunksScaleSink_CreationParams(DataSinkCreationParams):
    def __init__(self, url: Url, encoding: PrecomputedChunksEncoder) -> None:
        super().__init__(url)
        self.encoding = encoding

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "PrecomputedChunksScaleSink_CreationParams":
        value_obj = ensureJsonObject(value)
        return PrecomputedChunksScaleSink_CreationParams(
            url=Url.parse(ensureJsonString(value_obj.get("url"))),
            encoding=PrecomputedChunksEncoder.from_json_value(value_obj.get("encoding")),
        )

    def to_json_value(self) -> JsonObject:
        return {
            "url": self.url.to_json_value(),
            "encoding": self.encoding.to_json_value(),
            "__class__": self.__class__.__name__
        }

    def try_load(
        self,
        *,
        ebrains_user_token: Optional[UserToken],
        allowed_protocols: Sequence[Protocol] = (Protocol.HTTP, Protocol.HTTPS),
        dtype: "np.dtype[DT]",
        interval: Interval5D,
        chunk_size: Shape5D,
        location: Point5D,
        spatial_resolution: Tuple[int, int, int],
    ) -> Union[DataSink, UsageError]:
        fs_url = self.url.parent
        base_path = Path(self.url.path.name)

        filesystem = try_filesystem_from_url(url=fs_url, allowed_protocols=allowed_protocols, ebrains_user_token=ebrains_user_token)
        if not filesystem:
            return UsageError(f"Can't retrieve data from {fs_url}")

        sink = PrecomputedChunksSink.create(
            base_path=base_path, #FIXME
            filesystem=filesystem,
            info=PrecomputedChunksInfo(
                data_type=dtype,
                type_="image",
                num_channels=interval.shape.c, #FIXME: could there be a channel offset?
                scales=tuple([
                    PrecomputedChunksScale(
                        key=Path("exported_data"),
                        size=(interval.shape.x, interval.shape.y, interval.shape.z),
                        chunk_sizes=tuple([
                            (chunk_size.x, chunk_size.y, chunk_size.z)
                        ]),
                        encoding=RawEncoder(),
                        voxel_offset=(location.x, location.y, location.z),
                        resolution=spatial_resolution
                    )
                ]),
            )
        ).scale_sinks[0]
        return sink