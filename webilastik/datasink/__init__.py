from abc import ABC, abstractmethod
import json
from pathlib import PurePosixPath
from typing import Any, Protocol
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString

import numpy as np

from ndstructs.point5D import Shape5D, Interval5D
from ndstructs.array5D import Array5D
from webilastik.filesystem import JsonableFilesystem
from webilastik.utility.url import Url

class DataSinkWriter(Protocol):
    def write(self, data: Array5D):
        ...

class DataSink(ABC):
    def __init__(
        self,
        *,
        tile_shape: Shape5D,
        interval: Interval5D,
        dtype: "np.dtype[Any]", #FIXME: remove Any
    ):
        self.tile_shape = tile_shape
        self.interval = interval
        self.dtype = dtype # type: ignore

        self.shape = self.interval.shape
        self.location = interval.start

    @abstractmethod
    def create(self) -> "Exception | DataSinkWriter":
        pass

    @abstractmethod
    def write(self, data: Array5D) -> None:
        pass

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": self.__class__.__name__,
            "tile_shape": self.tile_shape.to_json_value(),
            "interval": self.interval.to_json_value(),
            "shape": self.shape.to_json_value(),
            "dtype": str(self.dtype.name), #type: ignore
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "DataSink":
        value_obj = ensureJsonObject(value)
        class_name = ensureJsonString(value_obj.get("__class__"))

        from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksScaleSink
        if class_name == PrecomputedChunksScaleSink.__name__:
            return PrecomputedChunksScaleSink.from_json_value(value)
        raise ValueError(f"Could not deserialize DataSink from {json.dumps(value)}")

class FsDataSink(DataSink):
    def __init__(
        self,
        *,
        filesystem: JsonableFilesystem,
        path: PurePosixPath,
        tile_shape: Shape5D,
        interval: Interval5D,
        dtype: "np.dtype[Any]",
    ):
        self.filesystem = filesystem
        self.path = path
        super().__init__(tile_shape=tile_shape, interval=interval, dtype=dtype)

    @property
    def url(self) -> Url:
        url = Url.parse(self.filesystem.geturl(self.path.as_posix()))
        assert url is not None
        return url

    def to_json_value(self) -> JsonObject:
        return {
            **super().to_json_value(),
            "filesystem": self.filesystem.to_json_value(),
            "path": self.path.as_posix(),
            "url": self.url.raw,
        }