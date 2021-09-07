from pathlib import Path
import json
from typing import Tuple
from webilastik.datasink import DataSink, DATASINK_FROM_JSON_CONSTRUCTORS

import numpy as np
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString
from webilastik.filesystem import JsonableFilesystem

from ndstructs.array5D import Array5D

from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksInfo, PrecomputedChunksScale


class PrecomputedChunksScaleSink(DataSink):
    # @privatemethod
    def __init__(
        self, *, path: Path, filesystem: JsonableFilesystem, scale: PrecomputedChunksScale, dtype: np.dtype
    ):
        super().__init__(
            tile_shape=scale.chunk_sizes[0], #FIXME: what if scale had multiple chunk sizes?
            interval=scale.size.to_interval5d(scale.voxel_offset),
            dtype=dtype,
            path=path,
        )
        self.filesystem = filesystem
        self.scale = scale

    def to_json_value(self) -> JsonObject:
        return {
            **super().to_json_value(),
            "filesystem": self.filesystem.to_json_value(),
            "scale": self.scale.to_json_value()
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "PrecomputedChunksScaleSink":
        value_obj = ensureJsonObject(value)
        return PrecomputedChunksScaleSink(
            path=Path(ensureJsonString(value_obj.get("path"))),
            filesystem=JsonableFilesystem.from_json_value(value_obj.get("filesystem")),
            scale=PrecomputedChunksScale.from_json_value(value_obj.get("scale")),
            dtype=np.dtype(ensureJsonString(value_obj.get("dtype"))), #type: ignore
        )

    def __getstate__(self) -> JsonObject:
        return self.to_json_value()

    def __setstate__(self, value: JsonValue):
        sink = PrecomputedChunksScaleSink.from_json_value(value)
        self.__init__(
            path=sink.path,
            filesystem=sink.filesystem,
            scale=sink.scale,
            dtype=sink.dtype, #type: ignore
        )

    @classmethod
    def create(
        cls,
        *,
        path: Path,
        resolution: Tuple[int, int, int],
        filesystem: JsonableFilesystem,
        info: PrecomputedChunksInfo,
    ) -> "PrecomputedChunksScaleSink":
        selected_scale=info.get_scale(resolution=resolution)
        if filesystem.exists(path.as_posix()):
            filesystem.removedir(path.as_posix())
        filesystem.makedirs(path.as_posix())
        with filesystem.openbin(path.joinpath("info").as_posix(), "w") as info_file:
            info_file.write(json.dumps(info.to_json_value()).encode("utf8"))
        for scale in info.scales:
            filesystem.makedirs(path.joinpath(scale.key).as_posix())
        return PrecomputedChunksScaleSink(path=path, filesystem=filesystem, scale=selected_scale, dtype=info.data_type)

    @classmethod
    def open(cls, *, path: Path, resolution: Tuple[int, int, int], filesystem: JsonableFilesystem) -> "PrecomputedChunksScaleSink":
        with filesystem.openbin(path.joinpath("info").as_posix(), "r") as f:
            info_json = f.read().decode("utf8")
        info = PrecomputedChunksInfo.from_json_value(json.loads(info_json))
        selected_scale = info.get_scale(resolution=resolution)
        return PrecomputedChunksScaleSink(path=path, filesystem=filesystem, scale=selected_scale, dtype=info.data_type)

    def write(self, data: Array5D):
        chunk_path = self.path / self.scale.get_tile_path(data.interval)
        # https://github.com/google/neuroglancer/tree/master/src/neuroglancer/datasource/precomputed#raw-chunk-encoding
        # "(...) data for the chunk is stored directly in little-endian binary format in [x, y, z, channel] Fortran order"
        with self.filesystem.openbin(chunk_path.as_posix(), "w") as f:
            f.write(self.scale.encoding.encode(data))

DATASINK_FROM_JSON_CONSTRUCTORS[PrecomputedChunksScaleSink.__name__] = PrecomputedChunksScaleSink.from_json_value