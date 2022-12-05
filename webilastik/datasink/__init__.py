from abc import ABC, abstractmethod
from pathlib import PurePosixPath
from typing import Any, Optional, Protocol, Tuple

import numpy as np

from ndstructs.point5D import Shape5D, Interval5D
from ndstructs.array5D import Array5D
from webilastik.filesystem import IFilesystem
from webilastik.server.rpc.dto import DataSinkDto, PrecomputedChunksSinkDto
from webilastik.utility.url import Url

class IDataSinkWriter(Protocol):
    @property
    def data_sink(self) -> "DataSink":
        ...
    def write(self, data: Array5D):
        ...

class DataSink(ABC):
    def __init__(
        self,
        *,
        tile_shape: Shape5D,
        interval: Interval5D,
        dtype: "np.dtype[Any]", #FIXME: remove Any
        resolution: Optional[Tuple[int, int, int]] = None,
    ):
        self.tile_shape = tile_shape
        self.interval = interval
        self.dtype = dtype
        self.resolution = resolution

        self.shape = self.interval.shape
        self.location = interval.start
        super().__init__()

    @abstractmethod
    def open(self) -> "Exception | IDataSinkWriter":
        pass

    @classmethod
    def create_from_message(cls, message: DataSinkDto) -> "DataSink | Exception": #FIXME: add other sinks
        if isinstance(message, PrecomputedChunksSinkDto):
            from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksSink
            return PrecomputedChunksSink.from_dto(message)
        from webilastik.datasink.n5_dataset_sink import N5DataSink
        return N5DataSink.from_dto(message)

    @abstractmethod
    def to_dto(self) -> DataSinkDto: #FIXME: add other sinks
        pass

class FsDataSink(DataSink):
    def __init__(
        self,
        *,
        filesystem: IFilesystem,
        path: PurePosixPath,
        tile_shape: Shape5D,
        interval: Interval5D,
        dtype: "np.dtype[Any]",
        resolution: Optional[Tuple[int, int, int]] = None
    ):
        self.filesystem = filesystem
        self.path = path
        super().__init__(
            tile_shape=tile_shape,
            interval=interval,
            dtype=dtype,
            resolution=resolution,
        )

    @property
    def url(self) -> Url:
        return self.filesystem.geturl(self.path)
