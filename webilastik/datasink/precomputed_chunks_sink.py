from pathlib import PurePosixPath
import json
from typing import Any

import numpy as np
from ndstructs.point5D import Point5D, Shape5D
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonInt, ensureJsonObject, ensureJsonString
from ndstructs.array5D import Array5D

from webilastik.datasink import FsDataSink, DATASINK_FROM_JSON_CONSTRUCTORS
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.filesystem import JsonableFilesystem
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksInfo, PrecomputedChunksScale
from webilastik.utility.url import Url

class PrecomputedChunksScaleSink(FsDataSink):
    def __init__(
        self,
        *,
        filesystem: JsonableFilesystem,
        info_dir: PurePosixPath, #path to dir containing with the info file
        scale: PrecomputedChunksScale,
        dtype: "np.dtype[Any]",
        num_channels: int,
    ):
        self.info_dir = info_dir
        self.scale = scale

        shape = Shape5D(x=scale.size[0], y=scale.size[1], z=scale.size[2], c=num_channels)
        location = Point5D(x=scale.voxel_offset[0], y=scale.voxel_offset[1], z=scale.voxel_offset[2])
        interval = shape.to_interval5d(offset=location)
        chunk_sizes_5d = [Shape5D(x=cs[0], y=cs[1], z=cs[2], c=num_channels) for cs in scale.chunk_sizes]

        super().__init__(
            filesystem=filesystem,
            path=info_dir,
            tile_shape=chunk_sizes_5d[0], #FIXME
            interval=interval,
            dtype=dtype,
        )

    @property
    def url(self) -> Url:
        return super().url.updated_with(
            hash_=f"resolution={self.scale.resolution[0]}_{self.scale.resolution[1]}_{self.scale.resolution[2]}"
        )

    def create(self) -> "Exception | None":
        info_path = self.info_dir.joinpath("info")
        scale_path = self.info_dir / self.scale.key

        if not self.filesystem.exists(info_path.as_posix()):
            _ = self.filesystem.makedirs(self.info_dir.as_posix())
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

    def to_datasource(self) -> PrecomputedChunksDataSource:
        return PrecomputedChunksDataSource(
            filesystem=self.filesystem,
            path=self.info_dir,
            resolution=self.scale.resolution,
        )

    def to_json_value(self) -> JsonObject:
        return {
            **super().to_json_value(),
            "filesystem": self.filesystem.to_json_value(),
            "info_dir": self.info_dir.as_posix(),
            "scale": self.scale.to_json_value(),
            "dtype": str(self.dtype),
            "num_channels": self.shape.c,
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "PrecomputedChunksScaleSink":
        value_obj = ensureJsonObject(value)
        return PrecomputedChunksScaleSink(
            filesystem=JsonableFilesystem.from_json_value(value_obj.get("filesystem")),
            info_dir=PurePosixPath(ensureJsonString(value_obj.get("info_dir"))),
            scale=PrecomputedChunksScale.from_json_value(value_obj.get("scale")),
            dtype=np.dtype(ensureJsonString(value_obj.get("dtype"))),
            num_channels=ensureJsonInt(value_obj.get("num_channels"))
        )

    def __getstate__(self) -> JsonObject:
        return self.to_json_value()

    def __setstate__(self, value: JsonValue):
        sink = PrecomputedChunksScaleSink.from_json_value(value)
        self.__init__(
            filesystem=sink.filesystem,
            info_dir=sink.info_dir,
            scale=sink.scale,
            dtype=sink.dtype,
            num_channels=sink.shape.c,
        )

    def write(self, data: Array5D):
        tile = data.interval
        assert tile.is_tile(tile_shape=self.tile_shape, full_interval=self.interval, clamped=True), f"Bad tile: {tile}"
        chunk_name = f"{tile.x[0]}-{tile.x[1]}_{tile.y[0]}-{tile.y[1]}_{tile.z[0]}-{tile.z[1]}"
        chunk_path = self.info_dir / self.scale.key / chunk_name
        with self.filesystem.openbin(chunk_path.as_posix(), "w") as f:
            _ = f.write(self.scale.encoding.encode(data))

DATASINK_FROM_JSON_CONSTRUCTORS[PrecomputedChunksScaleSink.__name__] = PrecomputedChunksScaleSink.from_json_value