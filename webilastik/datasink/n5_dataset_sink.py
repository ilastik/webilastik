from typing import Set
from pathlib import PurePosixPath
import json
from webilastik.filesystem import Filesystem

from ndstructs.array5D import Array5D

from webilastik.datasource.n5_attributes import N5DatasetAttributes
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
        attributes: N5DatasetAttributes
    ):
        super().__init__(
        dtype=attributes.dataType,
            tile_shape=attributes.blockSize,
            interval=attributes.dimensions.to_interval5d(),
        )
        self.outer_path = outer_path
        self.inner_path = inner_path
        self.full_path = outer_path.joinpath(inner_path.as_posix().lstrip("/"))
        self.attributes = attributes
        self.filesystem = filesystem

    def open(self) -> "Exception | N5Writer":
        _ = self.filesystem.makedirs(self.full_path.as_posix(), recreate=True)

        with self.filesystem.openbin(self.outer_path.joinpath("attributes.json").as_posix(), "w") as f:
            _ = f.write(json.dumps({"n5": "2.0.0"}).encode("utf8"))

        with self.filesystem.openbin(self.full_path.joinpath("attributes.json").as_posix(), "w") as f:
            _ = f.write(json.dumps(self.attributes.to_json_data()).encode("utf-8"))

        # create all directories in the constructor to avoid races when processing tiles
        created_dirs : Set[PurePosixPath] = set()
        for tile in self.attributes.interval.split(self.attributes.blockSize):
            dir_path = self.full_path / self.attributes.get_tile_path(tile).parent
            if dir_path and dir_path not in created_dirs:
                # print(f"Will create dir at {dir_path}")
                _ = self.filesystem.makedirs(dir_path.as_posix())
                created_dirs.add(dir_path)

        return N5Writer(self)


