from typing import Any, Optional, Set, Tuple
from pathlib import PurePosixPath
import json
import numpy as np
from ndstructs.point5D import Interval5D, Shape5D

from webilastik.server.rpc.dto import Interval5DDto, N5DataSinkDto, Shape5DDto, dtype_to_dto
from webilastik.filesystem import IFilesystem, create_filesystem_from_message

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
        tile_path = self._data_sink.path / self._data_sink.attributes.get_tile_path(data.interval)
        writing_result = self._data_sink.filesystem.create_file(
            path=tile_path,
            contents=tile.to_n5_bytes(
                axiskeys=self._data_sink.attributes.c_axiskeys, compression=self._data_sink.attributes.compression
            )
        )
        if isinstance(writing_result, Exception):
            raise writing_result #FIXME: return instead

class N5DataSink(DataSink):
    def __init__(
        self,
        *,
        filesystem: IFilesystem,
        path: PurePosixPath,
        interval: Interval5D,
        tile_shape: Shape5D,
        c_axiskeys: str,
        dtype: "np.dtype[Any]",
        compressor: N5Compressor,
        resolution: Tuple[int, int, int] = (1,1,1), #FIXME
    ):
        super().__init__(
            dtype=dtype,
            tile_shape=tile_shape,
            interval=interval,
            resolution=resolution
        )
        self.resolution = resolution
        self.path = path
        self.filesystem = filesystem
        self.c_axiskeys = c_axiskeys
        self.compressor = compressor
        self.attributes = N5DatasetAttributes(
            dimensions=self.interval.shape,
            c_axiskeys=self.c_axiskeys,
            blockSize=self.tile_shape,
            compression=self.compressor,
            dataType=self.dtype,
        )

        self.outer_path: Optional[PurePosixPath] = None
        while path != path.parent:
            if path.suffix.lower() == ".n5":
                self.outer_path = path
                break
            path = path.parent

    def open(self) -> "Exception | N5Writer":
        if self.outer_path:
            attributes_path = self.outer_path / "attributes.json"
            exists_result = self.filesystem.exists(attributes_path)
            if isinstance(exists_result, Exception):
                return exists_result
            if not exists_result:
                root_attrs = json.dumps({"n5": "2.0.0"}).encode("utf8")
                root_attrs_result = self.filesystem.create_file(path=attributes_path, contents=root_attrs)
                if isinstance(root_attrs_result, Exception):
                    return root_attrs_result

        dataset_attributes_write_result = self.filesystem.create_file(
            path=self.path.joinpath("attributes.json"),
            contents=json.dumps(self.attributes.to_dto().to_json_value()).encode("utf-8")
        )
        if isinstance(dataset_attributes_write_result, Exception):
            return dataset_attributes_write_result

        # create all directories in the constructor to avoid races when processing tiles
        created_dirs : Set[PurePosixPath] = set()
        for tile in self.interval.split(self.tile_shape):
            dir_path = self.path / self.attributes.get_tile_path(tile).parent
            if dir_path and dir_path not in created_dirs:
                # print(f"Will create dir at {dir_path}")
                dir_creation_result = self.filesystem.create_directory(dir_path)
                if isinstance(dir_creation_result, Exception):
                    return dir_creation_result
                created_dirs.add(dir_path)

        return N5Writer(self)

    def to_dto(self) -> N5DataSinkDto:
        return N5DataSinkDto(
            filesystem=self.filesystem.to_dto(),
            path=self.path.as_posix(),
            interval=Interval5DDto.from_interval5d(self.interval),
            tile_shape=Shape5DDto.from_shape5d(self.tile_shape),
            c_axiskeys=self.c_axiskeys,
            dtype=dtype_to_dto(self.dtype),
            compressor=self.compressor.to_dto(),
            spatial_resolution=self.resolution,
        )

    @staticmethod
    def from_dto(dto: N5DataSinkDto) -> "N5DataSink | Exception":
        fs_result = create_filesystem_from_message(dto.filesystem)
        if isinstance(fs_result, Exception):
            return fs_result
        return N5DataSink(
            filesystem=fs_result,
            path=PurePosixPath(dto.path),
            interval=dto.interval.to_interval5d(),
            tile_shape=dto.tile_shape.to_shape5d(),
            c_axiskeys=dto.c_axiskeys,
            dtype=np.dtype(dto.dtype),
            compressor=N5Compressor.create_from_dto(dto.compressor),
            resolution=dto.spatial_resolution
        )