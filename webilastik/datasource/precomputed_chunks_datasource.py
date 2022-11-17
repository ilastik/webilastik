from typing import Optional, Sequence, Tuple
from pathlib import PurePosixPath
import json
import logging

from webilastik.server.rpc.dto import Interval5DDto, PrecomputedChunksDataSourceDto, Shape5DDto, dtype_to_dto

from ndstructs.point5D import Point5D, Shape5D, Interval5D
from ndstructs.array5D import Array5D
from ndstructs.utils.json_serializable import ensureJsonIntTripplet
from fs.errors import ResourceNotFound

from webilastik.datasource import FsDataSource
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksInfo
from webilastik.filesystem import Filesystem
from webilastik.utility.url import Url

logger = logging.getLogger(__name__)

class PrecomputedChunksDataSource(FsDataSource):
    def __init__(
        self,
        *,
        filesystem: Filesystem,
        path: PurePosixPath,
        resolution: Tuple[int, int, int],
        location: Optional[Point5D] = None,
        chunk_size: Optional[Shape5D] = None,
    ):
        self.path = path
        self.filesystem = filesystem
        with self.filesystem.openbin(path.joinpath("info").as_posix(), "r") as f:
            info_json = f.read().decode("utf8")
        print(f"Got this info from a precomputed chunks:")
        print(info_json)
        info = PrecomputedChunksInfo.from_json_value(json.loads(info_json))
        self.scale = info.get_scale_5d(resolution=resolution)

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
            dtype=info.data_type,
            interval=self.scale.shape.to_interval5d(location or self.scale.location),
            spatial_resolution=self.scale.resolution, #FIXME: maybe delete this altogether?
        )

    def to_dto(self) -> PrecomputedChunksDataSourceDto:
        return PrecomputedChunksDataSourceDto(
            url=self.url.to_dto(),
            filesystem=self.filesystem.to_dto(),
            path=self.path.as_posix(),
            interval=Interval5DDto.from_interval5d(self.interval),
            spatial_resolution=self.spatial_resolution,
            tile_shape=Shape5DDto.from_shape5d(self.tile_shape),
            dtype=dtype_to_dto(self.dtype),
        )

    @staticmethod
    def from_dto(dto: PrecomputedChunksDataSourceDto) -> "PrecomputedChunksDataSource":
        return PrecomputedChunksDataSource(
            filesystem=Filesystem.create_from_message(dto.filesystem),
            path=PurePosixPath(dto.path),
            resolution=dto.spatial_resolution,
            chunk_size=dto.tile_shape.to_shape5d(),
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
        fs_result = Filesystem.from_url(url=fs_url)
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
