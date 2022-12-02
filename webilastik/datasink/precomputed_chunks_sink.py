from pathlib import PurePosixPath
import json
from typing import Any, Tuple, Literal

import numpy as np
from ndstructs.point5D import Shape5D, Interval5D
from ndstructs.array5D import Array5D

from webilastik.datasink import FsDataSink, IDataSinkWriter
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksInfo, PrecomputedChunksScale, PrecomputedChunksEncoder
from webilastik.filesystem import IFilesystem, create_filesystem_from_message
from webilastik.server.rpc.dto import Interval5DDto, PrecomputedChunksSinkDto, Shape5DDto
from webilastik.utility.url import Url

class PrecomputedChunksWriter(IDataSinkWriter):
    def __init__(self, data_sink: "PrecomputedChunksSink") -> None:
        super().__init__()
        self._data_sink = data_sink

    @property
    def data_sink(self) -> "PrecomputedChunksSink":
        return self._data_sink

    def write(self, data: Array5D):
        tile = data.interval
        assert tile.is_tile(tile_shape=self._data_sink.tile_shape, full_interval=self._data_sink.interval, clamped=True), f"Bad tile: {tile}"
        chunk_name = f"{tile.x[0]}-{tile.x[1]}_{tile.y[0]}-{tile.y[1]}_{tile.z[0]}-{tile.z[1]}"
        chunk_path = self._data_sink.path / self._data_sink.scale.key / chunk_name
        result = self._data_sink.filesystem.create_file(path=chunk_path, contents=self._data_sink.scale.encoding.encode(data))
        if isinstance(result, Exception):
            raise result #FIXME


class PrecomputedChunksSink(FsDataSink):
    def __init__(
        self,
        *,
        filesystem: IFilesystem,
        path: PurePosixPath,
        scale_key: PurePosixPath,
        tile_shape: Shape5D,
        interval: Interval5D,
        dtype: "np.dtype[Any]",
        resolution: Tuple[int, int, int],
        encoding: PrecomputedChunksEncoder,
    ):
        super().__init__(
            filesystem=filesystem,
            path=path,
            tile_shape=tile_shape,
            interval=interval,
            dtype=dtype,
        )
        self.scale_key = scale_key
        self.resolution = resolution
        self.encoding = encoding

        size = (interval.shape.x, interval.shape.y, interval.shape.z)
        offset = (interval.start.x, interval.start.y, interval.start.z)

        self.scale = PrecomputedChunksScale(
            key=self.scale_key,
            chunk_sizes=tuple([
                (tile_shape.x, tile_shape.y, tile_shape.z)
            ]),
            encoding=encoding,
            resolution=resolution,
            size=size,
            voxel_offset=offset,
        )

    @property
    def url(self) -> Url:
        return super().url.updated_with(
            hash_=f"resolution={self.resolution[0]}_{self.resolution[1]}_{self.resolution[2]}"
        )

    def open(self) -> "Exception | PrecomputedChunksWriter":
        info_path = self.path.joinpath("info")
        scale_path = self.path / self.scale_key.as_posix().lstrip("/")

        if not self.filesystem.exists(info_path):
            # _ = self.filesystem.makedirs(self.path.as_posix())
            info = PrecomputedChunksInfo(
                type_="image",
                data_type=self.dtype,
                num_channels=self.shape.c,
                scales=tuple([self.scale]),
            )
        else:
            info_result = PrecomputedChunksInfo.tryLoad(filesystem=self.filesystem, path=info_path)
            if isinstance(info_result, Exception):
                return info_result
            existing_info = info_result
            if existing_info.num_channels != self.shape.c:
                return ValueError(f"Unexpected num_channels in info: '{existing_info.num_channels}' instead of '{self.shape.c}'")
            if existing_info.data_type != self.dtype:
                return ValueError(f"Unexpected data type in info: '{existing_info.data_type}'")

            for scale in existing_info.scales:
                if scale.key == self.scale.key:
                    deletion_result = self.filesystem.delete(scale_path)
                    if isinstance(deletion_result, Exception):
                        return deletion_result
                    info = existing_info
                    break
            else:
                info = PrecomputedChunksInfo(
                    type_=existing_info.type_,
                    data_type=existing_info.data_type,
                    num_channels=existing_info.num_channels,
                    scales=tuple(
                        list(existing_info.scales) + [self.scale]
                    ),
                )

        # _ = self.filesystem.makedirs(scale_path.as_posix())

        info_write_result = self.filesystem.create_file(path=info_path, contents=json.dumps(info.to_json_value(), indent=4).encode("utf8"))
        if isinstance(info_write_result, Exception):
            return info_write_result
        return PrecomputedChunksWriter(data_sink=self)

    def to_datasource(self) -> PrecomputedChunksDataSource:
        return PrecomputedChunksDataSource(
            filesystem=self.filesystem,
            path=self.path,
            tile_shape=self.tile_shape,
            dtype=self.dtype,
            encoding=self.encoding,
            interval=self.interval,
            scale_key=self.scale_key,
            spatial_resolution=self.resolution,
        )

    def to_dto(self) -> PrecomputedChunksSinkDto:
        from webilastik.filesystem import BucketFs, HttpFs, OsFs
        assert isinstance(self.filesystem, (HttpFs, OsFs, BucketFs)) #FIXME
        type_name: Literal["uint8", "uint16", "uint32", "uint64", "float32"] = str(self.dtype) #type: ignore #FIXME
        return PrecomputedChunksSinkDto(
            filesystem=self.filesystem.to_dto(),
            path=self.path.as_posix(),
            dtype=type_name,
            tile_shape=Shape5DDto.from_shape5d(self.tile_shape),
            encoding=self.encoding.to_dto(),
            interval=Interval5DDto.from_interval5d(self.interval),
            resolution=self.resolution,
            scale_key=self.scale_key.as_posix(),
        )

    @classmethod
    def from_dto(cls, message: PrecomputedChunksSinkDto) -> "PrecomputedChunksSink":
        return PrecomputedChunksSink(
            filesystem=create_filesystem_from_message(message.filesystem),
            path=PurePosixPath(message.path),
            scale_key=PurePosixPath(message.scale_key),
            dtype=np.dtype(message.dtype), #FIXME?
            interval=message.interval.to_interval5d(),
            tile_shape=message.tile_shape.to_shape5d(),
            encoding=PrecomputedChunksEncoder.from_dto(message.encoding),
            resolution=message.resolution,
        )