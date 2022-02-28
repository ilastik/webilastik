from pathlib import PurePosixPath
from typing import Optional, Tuple

import skimage.io #type: ignore
import numpy as np
from ndstructs.array5D import Array5D
from ndstructs.point5D import Interval5D, Point5D, Shape5D
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonIntTripplet, ensureJsonObject, ensureJsonString, ensureOptional

from webilastik.datasource import FsDataSource
from webilastik.filesystem import JsonableFilesystem

class SkimageDataSource(FsDataSource):
    """A naive implementation of DataSource that can read images using skimage"""
    def __init__(
        self,
        *,
        path: PurePosixPath,
        location: Point5D = Point5D.zero(),
        filesystem: JsonableFilesystem,
        tile_shape: Optional[Shape5D] = None,
        spatial_resolution: Optional[Tuple[int, int, int]] = None,
    ):
        raw_data: np.ndarray = skimage.io.imread(filesystem.openbin(path.as_posix())) # type: ignore
        self._data = Array5D(raw_data, "yxc"[: len(raw_data.shape)], location=location)

        if tile_shape is None:
            tile_shape = Shape5D.hypercube(256).to_interval5d().clamped(self._data.shape).shape

        super().__init__(
            filesystem=filesystem,
            path=path,
            dtype=self._data.dtype, #type: ignore
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

    def to_json_value(self) -> JsonObject:
        return super().to_json_value()

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "SkimageDataSource":
        value_obj = ensureJsonObject(value)
        return SkimageDataSource(
            path=PurePosixPath(ensureJsonString(value_obj.get("path"))),
            location=ensureOptional(Point5D.from_json_value, value_obj.get("location")) or Point5D.zero(),
            filesystem=JsonableFilesystem.from_json_value(value_obj.get("filesystem")),
            tile_shape=ensureOptional(Shape5D.from_json_value, value_obj.get("tile_shape")),
            spatial_resolution=ensureOptional(ensureJsonIntTripplet, value_obj.get("spatial_resolution")),
        )

    def __getstate__(self) -> JsonObject:
        return self.to_json_value()

    def __setstate__(self, value_obj: JsonObject):
        self.__init__(
            path=PurePosixPath(ensureJsonString(value_obj.get("path"))),
            location=ensureOptional(Point5D.from_json_value, value_obj.get("location")) or Point5D.zero(),
            filesystem=JsonableFilesystem.from_json_value(value_obj.get("filesystem")),
            tile_shape=ensureOptional(Shape5D.from_json_value, value_obj.get("tile_shape")),
            spatial_resolution=ensureOptional(ensureJsonIntTripplet, value_obj.get("spatial_resolution")),
        )

FsDataSource.datasource_from_json_constructors[SkimageDataSource.__name__] = SkimageDataSource.from_json_value
