from typing import Optional, Tuple
from pathlib import Path
import json
import logging

from ndstructs.point5D import Point5D, Shape5D, Interval5D
from ndstructs.array5D import Array5D
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonIntTripplet, ensureJsonObject, ensureJsonString
from fs.errors import ResourceNotFound

from webilastik.datasource import DataSource
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksInfo
from webilastik.filesystem import JsonableFilesystem
from webilastik.utility.url import Url

logger = logging.getLogger(__name__)

class PrecomputedChunksDataSource(DataSource):
    def __init__(
        self,
        *,
        path: Path,
        resolution: Tuple[int, int, int],
        location: Optional[Point5D] = None,
        chunk_size: Optional[Shape5D] = None,
        filesystem: JsonableFilesystem,
    ):
        self.path = path
        self.filesystem = filesystem
        with self.filesystem.openbin(path.joinpath("info").as_posix(), "r") as f:
            info_json = f.read().decode("utf8")
        self.info = PrecomputedChunksInfo.from_json_value(json.loads(info_json))
        self.scale = self.info.get_scale_5d(resolution=resolution)

        if chunk_size:
            if chunk_size not in self.scale.chunk_sizes_5d:
                raise ValueError(f"Bad chunk size: {chunk_size}. Available are: {self.scale.chunk_sizes}")
            tile_shape = chunk_size
        else:
            tile_shape = self.scale.chunk_sizes_5d[0]

        base_url = Url.parse(filesystem.geturl(path.as_posix()))
        assert base_url is not None
        super().__init__( #type: ignore
            tile_shape=tile_shape,
            dtype=self.info.data_type, #type: ignore
            interval=self.scale.shape.to_interval5d(location or self.scale.location),
            axiskeys="zyxc",  # externally reported axiskeys are always c-ordered
            spatial_resolution=self.scale.resolution, #FIXME: maybe delete this altogether?
            url=base_url.updated_with(hash_=f"resolution={'_'.join(map(str, resolution))}")
        )

    def to_json_value(self) -> JsonObject:
        out = {**super().to_json_value()}
        out["path"] = self.path.as_posix()
        out["filesystem"] = self.filesystem.to_json_value()
        return out

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "PrecomputedChunksDataSource":
        value_obj = ensureJsonObject(value)
        raw_location = value_obj.get("location")
        raw_chunk_size = value_obj.get("chunk_size")
        return PrecomputedChunksDataSource(
            path=Path(ensureJsonString(value_obj.get("path"))),
            resolution=ensureJsonIntTripplet(value_obj.get("spatial_resolution")), # FIXME? change to just resolution?
            location=None if raw_location is None else Point5D.from_json_value(raw_location),
            chunk_size=None if raw_chunk_size is None else Shape5D.from_json_value(raw_chunk_size),
            filesystem=JsonableFilesystem.from_json_value(value_obj.get("filesystem")),
        )

    def __hash__(self) -> int:
        return hash((super().__hash__(), self.filesystem.desc(self.path.as_posix()), self.scale.key))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PrecomputedChunksDataSource) and
            super().__eq__(other) and
            self.scale.key == other.scale.key and
            self.filesystem.desc(self.path.as_posix()) == other.filesystem.desc(other.path.as_posix())
        )

    def _get_tile(self, tile: Interval5D) -> Array5D:
        if self.location != self.scale.voxel_offset:
            tile = tile.translated(-self.location).translated(self.scale.location)
        tile_path = self.path / self.scale.get_tile_path(tile)
        try:
            with self.filesystem.openbin(tile_path.as_posix()) as f:
                raw_tile_bytes = f.read()
            tile_5d = self.scale.encoding.decode(roi=tile, dtype=self.dtype, raw_chunk=raw_tile_bytes) #type: ignore
        except ResourceNotFound:
            logger.warn(f"tile {tile} not found. Returning zeros")
            tile_5d = Array5D.allocate(interval=tile, dtype=self.info.data_type, value=0)
        return tile_5d

    def __getstate__(self) -> JsonObject:
        return self.to_json_value()

    def __setstate__(self, data: JsonValue):
        ds = PrecomputedChunksDataSource.from_json_value(data)
        return self.__init__(
            path=ds.path,
            resolution=ds.spatial_resolution,
            location=ds.location,
            chunk_size=ds.tile_shape,
            filesystem=ds.filesystem,
        )

DataSource.datasource_from_json_constructors[PrecomputedChunksDataSource.__name__] = PrecomputedChunksDataSource.from_json_value
