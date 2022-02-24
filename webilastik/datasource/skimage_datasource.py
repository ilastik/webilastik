from pathlib import Path
from typing import Optional, Tuple

from ndstructs.point5D import Point5D, Shape5D
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString
import skimage.io #type: ignore

from webilastik.datasource import ArrayDataSource, DataSource
from webilastik.filesystem import JsonableFilesystem
from webilastik.utility.url import Url

class SkimageDataSource(ArrayDataSource):
    """A naive implementation of DataSource that can read images using skimage"""

    def __init__(
        self,
        *,
        path: Path,
        location: Point5D = Point5D.zero(),
        filesystem: JsonableFilesystem,
        tile_shape: Optional[Shape5D] = None,
        spatial_resolution: Optional[Tuple[int, int, int]] = None,
    ):
        self.path = path
        self.filesystem = filesystem
        raw_data: np.ndarray = skimage.io.imread(filesystem.openbin(path.as_posix())) # type: ignore
        axiskeys = "yxc"[: len(raw_data.shape)]
        url = Url.parse(filesystem.geturl(path.as_posix()))
        assert url is not None
        super().__init__(
            data=raw_data,
            axiskeys=axiskeys,
            location=location,
            tile_shape=tile_shape,
            spatial_resolution=spatial_resolution,
            url=url,
        )

    def to_json_value(self) -> JsonObject:
        out = {**DataSource.to_json_value(self)}
        out["path"] = self.path.as_posix()
        out["filesystem"] = self.filesystem.to_json_value()
        return out

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "SkimageDataSource":
        value_obj = ensureJsonObject(value)
        raw_location = value_obj.get("location")
        raw_tile_shape = value_obj.get("tile_shape")
        return SkimageDataSource(
            path=Path(ensureJsonString(value_obj.get("path"))),
            location=Point5D.zero() if raw_location is None else Point5D.from_json_value(raw_location),
            filesystem=JsonableFilesystem.from_json_value(value_obj.get("filesystem")),
            tile_shape=None if raw_tile_shape is None else Shape5D.from_json_value(raw_tile_shape)
        )

    def __getstate__(self) -> JsonObject:
        return self.to_json_value()

    def __setstate__(self, data: JsonObject):
        ds = SkimageDataSource.from_json_value(data)
        self.__init__(path=ds.path, filesystem=ds.filesystem, tile_shape=ds.tile_shape, location=ds.location)

DataSource.datasource_from_json_constructors[SkimageDataSource.__name__] = SkimageDataSource.from_json_value
