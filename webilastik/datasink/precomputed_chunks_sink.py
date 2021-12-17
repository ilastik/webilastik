from pathlib import Path
import json

import numpy as np
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString
from ndstructs.array5D import Array5D

from webilastik.datasink import DataSink, DATASINK_FROM_JSON_CONSTRUCTORS
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.filesystem import JsonableFilesystem
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksInfo, PrecomputedChunksScale5D

class PrecomputedChunksSink:
    def __init__(
        self,
        *,
        filesystem: JsonableFilesystem,
        base_path: Path,
        info: PrecomputedChunksInfo,
    ):
        self.filesystem = filesystem
        self.base_path = base_path
        self.info = info
        self.scale_sinks = tuple(
            PrecomputedChunksScaleSink(
                filesystem=filesystem,
                base_path=base_path,
                scale=scale,
                dtype=info.data_type, #type: ignore
            )
            for scale in info.scales_5d
        )

    @classmethod
    def create(
        cls,
        *,
        filesystem: JsonableFilesystem,
        base_path: Path, # path to the "directory" that should contain the info file
        info: PrecomputedChunksInfo,
    ) -> "PrecomputedChunksSink":
        if filesystem.exists(base_path.as_posix()):
            filesystem.removedir(base_path.as_posix())
        _ = filesystem.makedirs(base_path.as_posix())

        with filesystem.openbin(base_path.joinpath("info").as_posix(), "w") as info_file:
            _ = info_file.write(json.dumps(info.to_json_value()).encode("utf8"))

        for scale in info.scales_5d:
            scale_path = base_path.joinpath(scale.key.as_posix().lstrip("/"))
            _ = filesystem.makedirs(scale_path.as_posix())

        return  PrecomputedChunksSink(filesystem=filesystem, base_path=base_path, info=info)


class PrecomputedChunksScaleSink(DataSink):
    def __init__(
        self,
        *,
        filesystem: JsonableFilesystem,
        base_path: Path,
        scale: PrecomputedChunksScale5D,
        dtype: np.dtype, #type: ignore
    ):
        self.filesystem = filesystem
        self.base_path = base_path
        self.scale = scale

        super().__init__( #type: ignore
            tile_shape=self.scale.chunk_sizes_5d[0], #FIXME
            interval=self.scale.interval,
            dtype=dtype, #type: ignore
        )

    def to_datasource(self) -> PrecomputedChunksDataSource:
        return PrecomputedChunksDataSource(
            filesystem=self.filesystem,
            path=self.base_path,
            resolution=self.scale.resolution,
        )

    def to_json_value(self) -> JsonObject:
        return {
            **super().to_json_value(),
            "filesystem": self.filesystem.to_json_value(),
            "base_path": self.base_path.as_posix(),
            "scale": self.scale.to_json_value(),
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "PrecomputedChunksScaleSink":
        value_obj = ensureJsonObject(value)
        return PrecomputedChunksScaleSink(
            filesystem=JsonableFilesystem.from_json_value(value_obj.get("filesystem")),
            base_path=Path(ensureJsonString(value_obj.get("base_path"))),
            scale=PrecomputedChunksScale5D.from_json_value(value_obj.get("scale")),
            dtype=np.dtype(ensureJsonString(value_obj.get("dtype"))), #type: ignore
        )

    def __getstate__(self) -> JsonObject:
        return self.to_json_value()

    def __setstate__(self, value: JsonValue):
        sink = PrecomputedChunksScaleSink.from_json_value(value)
        self.__init__( #type: ignore
            filesystem=sink.filesystem,
            base_path=sink.base_path,
            scale=sink.scale,
            dtype=sink.dtype, #type: ignore
        )

    def write(self, data: Array5D):
        chunk_path = self.base_path / self.scale.get_tile_path(data.interval)
        print(f"Writing {data} to chunk at {chunk_path}")
        # https://github.com/google/neuroglancer/tree/master/src/neuroglancer/datasource/precomputed#raw-chunk-encoding
        # "(...) data for the chunk is stored directly in little-endian binary format in [x, y, z, channel] Fortran order"
        with self.filesystem.openbin(chunk_path.as_posix(), "w") as f:
            _ = f.write(self.scale.encoding.encode(data))

DATASINK_FROM_JSON_CONSTRUCTORS[PrecomputedChunksScaleSink.__name__] = PrecomputedChunksScaleSink.from_json_value