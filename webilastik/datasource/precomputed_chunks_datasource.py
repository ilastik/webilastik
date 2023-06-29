from typing import Optional, Tuple, Any
from pathlib import PurePosixPath
import logging

import numpy as np

from ndstructs.point5D import Shape5D, Interval5D
from ndstructs.array5D import Array5D
from ndstructs.utils.json_serializable import ensureJsonIntTripplet

from webilastik.datasource import FsDataSource
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksEncoder, PrecomputedChunksInfo
from webilastik.filesystem import FsFileNotFoundException, IFilesystem, create_filesystem_from_message
from webilastik.utility.url import Url
from webilastik.server.rpc.dto import Interval5DDto, PrecomputedChunksDataSourceDto, Shape5DDto, dtype_to_dto


logger = logging.getLogger(__name__)

class PrecomputedChunksDataSource(FsDataSource):
    def __init__(
        self,
        *,
        filesystem: IFilesystem,
        path: PurePosixPath,
        scale_key: PurePosixPath,
        tile_shape: Shape5D,
        interval: Interval5D,
        dtype: "np.dtype[Any]",
        spatial_resolution: Tuple[int, int, int],
        encoding: PrecomputedChunksEncoder,
    ):
        self.encoding = encoding
        self.scale_key = scale_key
        self.scale_path = path / PurePosixPath("/").joinpath(self.scale_key).as_posix().lstrip("/")
        super().__init__(
            # "The (...) data (...) chunk is stored directly in little-endian binary format in [x, y, z, channel] Fortran order"
            c_axiskeys_on_disk="xyzc"[::-1],
            filesystem=filesystem,
            path=path,
            tile_shape=tile_shape,
            dtype=dtype,
            interval=interval,
            spatial_resolution=spatial_resolution, #FIXME: maybe delete this altogether?
        )

    @classmethod
    def try_load(
        cls,
        *,
        filesystem: IFilesystem,
        path: PurePosixPath,
        spatial_resolution: Tuple[int, int, int],
        chunk_size: Optional[Shape5D] = None,
    ) -> "PrecomputedChunksDataSource | None | Exception":
        info_result = PrecomputedChunksInfo.tryLoad(filesystem=filesystem, path=path / "info")
        if isinstance(info_result, FsFileNotFoundException):
            return None
        if isinstance(info_result, Exception):
            return info_result
        scale = info_result.get_scale_5d(resolution=spatial_resolution)
        if isinstance(scale, Exception):
            return scale
        if chunk_size:
            if chunk_size not in scale.chunk_sizes_5d:
                return ValueError(f"Bad chunk size: {chunk_size}. Available are: {scale.chunk_sizes}")
            tile_shape = chunk_size
        else:
            tile_shape = scale.chunk_sizes_5d[0]

        return PrecomputedChunksDataSource(
            dtype=info_result.data_type,
            encoding=scale.encoding,
            filesystem=filesystem,
            path=path,
            interval=scale.interval,
            scale_key=scale.key,
            spatial_resolution=spatial_resolution,
            tile_shape=tile_shape,
        )


    def to_dto(self) -> PrecomputedChunksDataSourceDto:
        return PrecomputedChunksDataSourceDto(
            url=self.url.to_dto(),
            filesystem=self.filesystem.to_dto(),
            path=self.path.as_posix(),
            scale_key=self.scale_key.as_posix(),
            interval=Interval5DDto.from_interval5d(self.interval),
            spatial_resolution=self.spatial_resolution,
            tile_shape=Shape5DDto.from_shape5d(self.tile_shape),
            dtype=dtype_to_dto(self.dtype),
            encoder=self.encoding.to_dto(),
        )

    @staticmethod
    def from_dto(dto: PrecomputedChunksDataSourceDto) -> "PrecomputedChunksDataSource | Exception":
        fs_result = create_filesystem_from_message(dto.filesystem)
        if isinstance(fs_result, Exception):
            return fs_result

        return PrecomputedChunksDataSource(
            filesystem=fs_result,
            path=PurePosixPath(dto.path),
            scale_key=PurePosixPath(dto.scale_key),
            dtype=np.dtype(dto.dtype),
            interval=dto.interval.to_interval5d(),
            encoding=PrecomputedChunksEncoder.from_dto(dto.encoder),
            spatial_resolution=dto.spatial_resolution,
            tile_shape=dto.tile_shape.to_shape5d(),
        )

    @property
    def url(self) -> Url:
        resolution_str = f"{self.spatial_resolution[0]}_{self.spatial_resolution[1]}_{self.spatial_resolution[2]}"
        return super().url.updated_with(datascheme="precomputed", hash_=f"resolution={resolution_str}")

    @classmethod
    def get_resolution_from_url(cls, url: Url) -> "Tuple[int, int, int] | None | Exception":
        resolution_str = url.get_hash_params().get("resolution")
        if resolution_str is None:
            return None
        try:
            return ensureJsonIntTripplet(tuple(int(axis) for axis in resolution_str.split("_")))
        except Exception:
            return Exception(f"Bad resolution fragment parameter: {resolution_str}")

    @classmethod
    def supports_url(cls, url: Url) -> bool:
        return url.datascheme == "precomputed"

    @classmethod
    def try_open_scales(
        cls, fs: IFilesystem, path: PurePosixPath, resolution: Optional[Tuple[int, int, int]]
    ) -> "Tuple[PrecomputedChunksDataSource, ...] | None | Exception":
        if resolution is not None:
            datasource_result = cls.try_load(filesystem=fs, path=path, spatial_resolution=resolution)
            if isinstance(datasource_result, (Exception, type(None))):
                return datasource_result
            return (datasource_result, )
        precomp_info_result = PrecomputedChunksInfo.tryLoad(filesystem=fs, path=path / "info")
        if isinstance(precomp_info_result, Exception):
            return precomp_info_result
        return tuple(
            PrecomputedChunksDataSource(
                filesystem=fs,
                path=path,
                scale_key=scale.key,
                encoding=scale.encoding,
                dtype=precomp_info_result.data_type,
                interval=scale.interval,
                spatial_resolution=scale.resolution,
                tile_shape=scale.chunk_sizes_5d[0],
            )
            for scale in precomp_info_result.scales_5d
        )

    @classmethod
    def try_open_as_scale_path(cls, *, fs: IFilesystem, scale_path: PurePosixPath) -> "PrecomputedChunksDataSource | None | Exception":
        original_path = scale_path #FIXME: maybe don't modify the original?
        scale_path = PurePosixPath("/") / scale_path
        for scale_path_parent in scale_path.parents:
            precomp_info_result = PrecomputedChunksInfo.tryLoad(filesystem=fs, path=scale_path_parent / "info")
            if isinstance(precomp_info_result, FsFileNotFoundException):
                continue
            if isinstance(precomp_info_result, Exception):
                return precomp_info_result
            relative_scale_path = scale_path.relative_to(scale_path_parent).as_posix()
            scales = [s for s in precomp_info_result.scales_5d if s.key.as_posix().lstrip("/").rstrip("/") == relative_scale_path]
            if len(scales) == 0:
                return FsFileNotFoundException(original_path)
            if len(scales) != 1:
                return Exception(f"Expected a single scale, found {len(scales)}")
            scale = scales[0]
            return PrecomputedChunksDataSource(
                dtype=precomp_info_result.data_type,
                encoding=scale.encoding,
                filesystem=fs,
                path=scale_path_parent,
                interval=scale.interval,
                scale_key=scale.key,
                spatial_resolution=scale.resolution,
                tile_shape=scale.chunk_sizes_5d[0],
            )
        return None


    def __hash__(self) -> int:
        return hash((self.url, self.scale_key, self.interval))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PrecomputedChunksDataSource) and
            super().__eq__(other) and
            self.encoding == other.encoding and
            self.scale_key == other.scale_key
        )

    def get_tile_path(self, tile: Interval5D) -> PurePosixPath:
        return self.scale_path / f"{tile.x[0]}-{tile.x[1]}_{tile.y[0]}-{tile.y[1]}_{tile.z[0]}-{tile.z[1]}"

    def _get_tile(self, tile: Interval5D) -> Array5D:
        assert tile.is_tile(tile_shape=self.tile_shape, full_interval=self.interval, clamped=True), f"Bad tile: {tile}"
        tile_path = self.get_tile_path(tile)
        raw_tile_bytes = self.filesystem.read_file(tile_path)
        if isinstance(raw_tile_bytes, FsFileNotFoundException):
            logger.warn(f"tile {tile} not found. Returning zeros")
            return Array5D.allocate(interval=tile, dtype=self.dtype, value=0)
        if isinstance(raw_tile_bytes, Exception):
            raise raw_tile_bytes #FIXME: return instead
        return self.encoding.decode(roi=tile, dtype=self.dtype, raw_chunk=raw_tile_bytes)
