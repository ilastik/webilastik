from pathlib import PurePosixPath
import json
from typing import Any, Tuple, Literal

import numpy as np
from ndstructs.point5D import Shape5D, Interval5D
from ndstructs.array5D import Array5D

from webilastik.datasink import FsDataSink, IDataSinkWriter
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksInfo, PrecomputedChunksScale, PrecomputedChunksEncoder
from webilastik.filesystem import Filesystem
from webilastik.filesystem.bucket_fs import BucketFs
from webilastik.filesystem.http_fs import HttpFs
from webilastik.filesystem.osfs import OsFs
from webilastik.server.message_schema import Interval5DMessage, PrecomputedChunksSinkMessage, Shape5DMessage
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
        with self._data_sink.filesystem.openbin(chunk_path.as_posix(), "w") as f:
            _ = f.write(self._data_sink.scale.encoding.encode(data))


class PrecomputedChunksSink(FsDataSink):
    def __init__(
        self,
        *,
        filesystem: Filesystem,
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
        scale_path = self.path / self.scale_key

        if not self.filesystem.exists(info_path.as_posix()):
            _ = self.filesystem.makedirs(self.path.as_posix())
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
                    self.filesystem.removedir(scale_path.as_posix())
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

        _ = self.filesystem.makedirs(scale_path.as_posix())

        with self.filesystem.openbin(info_path.as_posix(), "w") as info_file:
            _ = info_file.write(json.dumps(info.to_json_value(), indent=4).encode("utf8"))
        return PrecomputedChunksWriter(data_sink=self)

    def to_datasource(self) -> PrecomputedChunksDataSource:
        return PrecomputedChunksDataSource(
            filesystem=self.filesystem,
            path=self.path,
            resolution=self.resolution,
        )

    def to_message(self) -> PrecomputedChunksSinkMessage:
        assert isinstance(self.filesystem, (HttpFs, OsFs, BucketFs)) #FIXME
        type_name: Literal["uint8", "uint16", "uint32", "uint64", "float32"] = str(self.dtype) #type: ignore #FIXME
        return PrecomputedChunksSinkMessage(
            filesystem=self.filesystem.to_message(),
            path=self.path.as_posix(),
            dtype=type_name,
            tile_shape=Shape5DMessage.from_shape5d(self.tile_shape),
            encoding=self.encoding.to_message(),
            interval=Interval5DMessage.from_interval5d(self.interval),
            resolution=self.resolution,
            scale_key=self.scale_key.as_posix(),
        )

    @classmethod
    def from_message(cls, message: PrecomputedChunksSinkMessage) -> "PrecomputedChunksSink":
        return PrecomputedChunksSink(
            filesystem=Filesystem.create_from_message(message.filesystem),
            path=PurePosixPath(message.path),
            scale_key=PurePosixPath(message.scale_key),
            dtype=np.dtype(message.dtype), #FIXME?
            interval=message.interval.to_interval5d(),
            tile_shape=message.tile_shape.to_shape5d(),
            encoding=PrecomputedChunksEncoder.from_message(message.encoding),
            resolution=message.resolution,
        )

    def __getstate__(self) -> PrecomputedChunksSinkMessage:
        return self.to_message()

    def __setstate__(self, message: PrecomputedChunksSinkMessage):
        self.__init__(
            filesystem=Filesystem.create_from_message(message.filesystem),
            path=PurePosixPath(message.path),
            scale_key=PurePosixPath(message.scale_key),
            dtype=np.dtype(message.dtype), #FIXME?
            interval=message.interval.to_interval5d(),
            tile_shape=message.tile_shape.to_shape5d(),
            encoding=PrecomputedChunksEncoder.from_message(message.encoding),
            resolution=message.resolution,
        )