from typing import Set
from pathlib import PurePosixPath
import json
from webilastik.filesystem import JsonableFilesystem

from ndstructs.array5D import Array5D

from webilastik.datasource.n5_attributes import N5DatasetAttributes
from webilastik.datasource.n5_datasource import N5Block
from webilastik.datasink import DataSink, DataSinkWriter

class N5DatasetSink(DataSink):
    # @privatemethod
    def __init__(
        self,
        *,
        filesystem: JsonableFilesystem,
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

    def create(self) -> "Exception | DataSinkWriter":
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

        return self #FIXME? maybe a different class?

    def write(self, data: Array5D) -> None:
        tile = N5Block.fromArray5D(data)
        tile_path = self.full_path / self.attributes.get_tile_path(data.interval)
        with self.filesystem.openbin(tile_path.as_posix(), "w") as f:
            _ = f.write(tile.to_n5_bytes(axiskeys=self.attributes.c_axiskeys, compression=self.attributes.compression))
