#pyright: strict

from pathlib import PurePosixPath
from typing import Optional, Sequence, Tuple, Any

import skimage.io #type: ignore
import numpy as np
from ndstructs.array5D import Array5D
from ndstructs.point5D import Interval5D, Point5D, Shape5D

from webilastik.datasource import FsDataSource
from webilastik.filesystem import Filesystem
from webilastik.utility.url import Url

class SkimageDataSource(FsDataSource):
    """A naive implementation of DataSource that can read images using skimage"""
    def __init__(
        self,
        *,
        path: PurePosixPath,
        location: Point5D = Point5D.zero(),
        filesystem: Filesystem,
        tile_shape: Optional[Shape5D] = None,
        spatial_resolution: Optional[Tuple[int, int, int]] = None,
    ):
        raw_data: "np.ndarray[Any, Any]" = skimage.io.imread(filesystem.openbin(path.as_posix())) # type: ignore
        c_axiskeys_on_disk = "yxc"[: len(raw_data.shape)]
        self._data = Array5D(raw_data, axiskeys=c_axiskeys_on_disk, location=location)

        if tile_shape is None:
            tile_shape = Shape5D.hypercube(256).to_interval5d().clamped(self._data.shape).shape

        super().__init__(
            c_axiskeys_on_disk=c_axiskeys_on_disk,
            filesystem=filesystem,
            path=path,
            dtype=self._data.dtype,
            interval=self._data.interval,
            tile_shape=tile_shape,
            spatial_resolution=spatial_resolution,
        )

    def _get_tile(self, tile: Interval5D) -> Array5D:
        return self._data.cut(tile, copy=True)

    def __hash__(self) -> int:
        return super().__hash__()

    def __eq__(self, other: object) -> bool:
        return super().__eq__(other)

    @classmethod
    def supports_url(cls, url: Url) -> bool:
        return url.datascheme == None and url.path.suffix in (".png", ".jpg", ".jpeg", ".bmp", ".gif")

    @classmethod
    def from_url(cls, url: Url) -> "Sequence[SkimageDataSource] | Exception":
        if not cls.supports_url(url):
            return Exception(f"Unsupported url: {url}")
        fs_url = url.parent.schemeless().hashless()
        fs_result = Filesystem.from_url(url=fs_url)
        if isinstance(fs_result, Exception):
            return fs_result
        path = PurePosixPath(url.path.name)
        try:
            return [SkimageDataSource(path=path, filesystem=fs_result)]
        except Exception as e:
            return e

