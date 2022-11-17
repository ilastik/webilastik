from typing import Any, Set
from pathlib import PurePosixPath
import json
import numpy as np
from ndstructs.point5D import Interval5D, Shape5D

from webilastik.server.rpc.dto import Interval5DDto, N5DataSinkDto, Shape5DDto, dtype_to_dto
from webilastik.filesystem import Filesystem

from ndstructs.array5D import Array5D

from webilastik.datasource.n5_attributes import N5Compressor, N5DatasetAttributes
from webilastik.datasource.n5_datasource import N5Block
from webilastik.datasink import DataSink, IDataSinkWriter

class N5Writer(IDataSinkWriter):
    def __init__(self, data_sink: "N5DataSink") -> None:
        super().__init__()
        self._data_sink = data_sink

    @property
    def data_sink(self) -> "N5DataSink":
        return self._data_sink

    def write(self, data: Array5D) -> None:
        tile = N5Block.fromArray5D(data)
        tile_path = self._data_sink.full_path / self._data_sink.attributes.get_tile_path(data.interval)
        with self._data_sink.filesystem.openbin(tile_path.as_posix(), "w") as f:
            _ = f.write(tile.to_n5_bytes(
                axiskeys=self._data_sink.attributes.c_axiskeys, compression=self._data_sink.attributes.compression
            ))

class N5DataSink(DataSink):
    def __init__(
        self,
        *,
        filesystem: Filesystem,
        outer_path: PurePosixPath,
        inner_path: PurePosixPath,
        interval: Interval5D,
        tile_shape: Shape5D,
        c_axiskeys: str,
        dtype: "np.dtype[Any]",
        compressor: N5Compressor,
    ):
        super().__init__(
            dtype=dtype,
            tile_shape=tile_shape,
            interval=interval,
        )
        self.outer_path = outer_path
        self.inner_path = inner_path
        self.full_path = outer_path.joinpath(inner_path.as_posix().lstrip("/"))
        self.filesystem = filesystem
        self.c_axiskeys = c_axiskeys
        self.compressor = compressor
        self.attributes = N5DatasetAttributes(
            dimensions=self.interval.shape,
            c_axiskeys=self.c_axiskeys,
            blockSize=self.tile_shape,
            compression=self.compressor,
            dataType=self.dtype,
            location=self.interval.start
        )


    def open(self) -> "Exception | N5Writer":
        _ = self.filesystem.makedirs(self.full_path.as_posix(), recreate=True)

        with self.filesystem.openbin(self.outer_path.joinpath("attributes.json").as_posix(), "w") as f:
            _ = f.write(json.dumps({"n5": "2.0.0"}).encode("utf8"))

        with self.filesystem.openbin(self.full_path.joinpath("attributes.json").as_posix(), "w") as f:
            _ = f.write(json.dumps(self.attributes.to_json_data()).encode("utf-8"))

        # create all directories in the constructor to avoid races when processing tiles
        created_dirs : Set[PurePosixPath] = set()
        for tile in self.interval.split(self.tile_shape):
            dir_path = self.full_path / self.attributes.get_tile_path(tile).parent
            if dir_path and dir_path not in created_dirs:
                # print(f"Will create dir at {dir_path}")
                _ = self.filesystem.makedirs(dir_path.as_posix())
                created_dirs.add(dir_path)

        return N5Writer(self)

    def to_dto(self) -> N5DataSinkDto:
        return N5DataSinkDto(
            filesystem=self.filesystem.to_dto(),
            outer_path=self.outer_path.as_posix(),
            inner_path=self.inner_path.as_posix(),
            interval=Interval5DDto.from_interval5d(self.interval),
            tile_shape=Shape5DDto.from_shape5d(self.tile_shape),
            c_axiskeys=self.c_axiskeys,
            dtype=dtype_to_dto(self.dtype),
            compressor=self.compressor.to_dto(),
        )

    @staticmethod
    def from_dto(dto: N5DataSinkDto) -> "N5DataSink":
        return N5DataSink(
            filesystem=Filesystem.create_from_message(dto.filesystem),
            outer_path=PurePosixPath(dto.outer_path),
            inner_path=PurePosixPath(dto.inner_path),
            interval=dto.interval.to_interval5d(),
            tile_shape=dto.tile_shape.to_shape5d(),
            c_axiskeys=dto.c_axiskeys,
            dtype=np.dtype(dto.dtype),
            compressor=N5Compressor.create_from_dto(dto.compressor),
        )