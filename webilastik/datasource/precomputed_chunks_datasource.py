from typing import Optional, Sequence, Tuple, Any
from pathlib import PurePosixPath
import json
import logging

from ndstructs.point5D import Point5D, Shape5D, Interval5D
from ndstructs.array5D import Array5D
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonIntTripplet, ensureJsonObject, ensureJsonString
from fs.errors import ResourceNotFound
import numpy as np

from webilastik.datasource import FsDataSource
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksInfo, PrecomputedChunksScale5D
from webilastik.filesystem import JsonableFilesystem
from webilastik.utility.url import Url

logger = logging.getLogger(__name__)

class PrecomputedChunksDataSource(FsDataSource):
    def __init__(
        self,
        *,
        path: PurePosixPath,
        resolution: Tuple[int, int, int],
        location: Optional[Point5D] = None,
        chunk_size: Optional[Shape5D] = None,
        filesystem: JsonableFilesystem,
        scale_and_dtype: "Tuple[PrecomputedChunksScale5D, np.dtype[Any]] | None" = None,
    ):
        self.path = path
        self.filesystem = filesystem
        if scale_and_dtype is None:
            with self.filesystem.openbin(path.joinpath("info").as_posix(), "r") as f:
                info_json = f.read().decode("utf8")
            print(f"Got this info from a precomputed chunks:")
            print(info_json)
            info = PrecomputedChunksInfo.from_json_value(json.loads(info_json))
            self.scale = info.get_scale_5d(resolution=resolution)
            dtype = info.data_type
        else:
            self.scale, dtype = scale_and_dtype

        if chunk_size:
            if chunk_size not in self.scale.chunk_sizes_5d:
                raise ValueError(f"Bad chunk size: {chunk_size}. Available are: {self.scale.chunk_sizes}")
            tile_shape = chunk_size
        else:
            tile_shape = self.scale.chunk_sizes_5d[0]

        base_url = Url.parse(filesystem.geturl(path.as_posix()))
        assert base_url is not None
        super().__init__(
            # "The (...) data (...) chunk is stored directly in little-endian binary format in [x, y, z, channel] Fortran order"
            c_axiskeys_on_disk="xyzc"[::-1],
            filesystem=filesystem,
            path=path,
            tile_shape=tile_shape,
            dtype=dtype,
            interval=self.scale.shape.to_interval5d(location or self.scale.location),
            spatial_resolution=self.scale.resolution, #FIXME: maybe delete this altogether?
        )

    @property
    def url(self) -> Url:
        resolution_str = f"{self.spatial_resolution[0]}_{self.spatial_resolution[1]}_{self.spatial_resolution[2]}"
        return super().url.updated_with(datascheme="precomputed", hash_=f"resolution={resolution_str}")

    @classmethod
    def supports_url(cls, url: Url) -> bool:
        return url.datascheme == "precomputed"

    @classmethod
    def from_url(cls, url: Url) -> "Sequence[PrecomputedChunksDataSource] | Exception":
        if not cls.supports_url(url):
            return Exception(f"Unsupported url: {url}")
        fs_url = url.parent.schemeless().hashless()
        fs_result = JsonableFilesystem.from_url(url=fs_url)
        if isinstance(fs_result, Exception):
            return fs_result
        fs = fs_result
        path = PurePosixPath(url.path.name)

        precomp_info_result = PrecomputedChunksInfo.tryLoad(filesystem=fs, path=path / "info")
        if isinstance(precomp_info_result, Exception):
            return precomp_info_result
        info = precomp_info_result

        resolution_str = url.get_hash_params().get("resolution")
        if resolution_str is None:
            return [
                PrecomputedChunksDataSource(filesystem=fs_result, path=path, resolution=scale.resolution)
                for scale in info.scales
            ]
        try:
            resolution_tripplet = ensureJsonIntTripplet(tuple(int(axis) for axis in resolution_str.split("_")))
        except Exception:
            return Exception(f"Bad resolution fragment parameter: {resolution_str}")
        resolution_options = [scale.resolution for scale in info.scales]
        if resolution_tripplet not in resolution_options:
            return Exception(f"Bad 'resolution' tripplet in url: {url}. Options are {resolution_options}")
        return [PrecomputedChunksDataSource(filesystem=fs, path=path, resolution=resolution_tripplet)]

    def to_json_value(self) -> JsonObject:
        return {
            **super().to_json_value(),
            "scale": self.scale.to_json_value(),
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "PrecomputedChunksDataSource":
        value_obj = ensureJsonObject(value)
        raw_location = value_obj.get("location")
        raw_chunk_size = value_obj.get("chunk_size")
        raw_scale = ensureJsonObject(value_obj.get("scale"))
        shape = Shape5D.from_json_value(value_obj.get("shape"))
        scale = PrecomputedChunksScale5D.from_json_value(
            {**raw_scale, "num_channels": shape.c}
        )
        dtype = np.dtype(ensureJsonString(value_obj.get("dtype")))
        return PrecomputedChunksDataSource(
            path=PurePosixPath(ensureJsonString(value_obj.get("path"))),
            resolution=ensureJsonIntTripplet(value_obj.get("spatial_resolution")), # FIXME? change to just resolution?
            location=None if raw_location is None else Point5D.from_json_value(raw_location),
            chunk_size=None if raw_chunk_size is None else Shape5D.from_json_value(raw_chunk_size),
            filesystem=JsonableFilesystem.from_json_value(value_obj.get("filesystem")),
            scale_and_dtype=(scale, dtype),
        )

    def __hash__(self) -> int:
        return hash((self.url, self.scale.key, self.location))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PrecomputedChunksDataSource) and
            self.url == other.url and
            self.scale.key == other.scale.key and
            self.location == other.location
        )

    def _get_tile(self, tile: Interval5D) -> Array5D:
        if self.location != self.scale.voxel_offset:
            tile = tile.translated(-self.location).translated(self.scale.location)
        tile_path = self.path / self.scale.get_tile_path(tile)
        try:
            with self.filesystem.openbin(tile_path.as_posix()) as f:
                raw_tile_bytes = f.read()
            tile_5d = self.scale.encoding.decode(roi=tile, dtype=self.dtype, raw_chunk=raw_tile_bytes)
        except ResourceNotFound:
            logger.warn(f"tile {tile} not found. Returning zeros")
            tile_5d = Array5D.allocate(interval=tile, dtype=self.dtype, value=0)
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
            scale_and_dtype=(ds.scale, ds.dtype),
        )

FsDataSource.datasource_from_json_constructors[PrecomputedChunksDataSource.__name__] = PrecomputedChunksDataSource.from_json_value
