from pathlib import PurePosixPath
from typing import Optional, Tuple, cast
import json

from ndstructs.array5D import Array5D

from webilastik.datasource import FsDataSource, guess_axiskeys
from webilastik.filesystem import JsonableFilesystem
from webilastik.utility.url import Url

import h5py
from ndstructs.point5D import Interval5D, Point5D, Shape5D
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonIntTripplet, ensureJsonObject, ensureJsonString, ensureOptional

class H5DataSource(FsDataSource):
    _dataset: h5py.Dataset
    def __init__(
        self,
        *,
        outer_path: PurePosixPath,
        inner_path: PurePosixPath,
        location: Point5D = Point5D.zero(),
        filesystem: JsonableFilesystem,
        spatial_resolution: Optional[Tuple[int, int, int]] = None
    ):
        self.outer_path = outer_path
        self.inner_path = inner_path
        self.filesystem = filesystem
        binfile = filesystem.openbin(outer_path.as_posix())
        f = h5py.File(binfile, "r")
        try:
            dataset = f[inner_path.as_posix()]
            if not isinstance(dataset, h5py.Dataset):
                raise ValueError(f"{inner_path} is not a Dataset")
            self.axiskeys = self.getAxisKeys(dataset)
            self._dataset = cast(h5py.Dataset, dataset)
            tile_shape = Shape5D.create(raw_shape=self._dataset.chunks or self._dataset.shape, axiskeys=self.axiskeys)
            base_url = Url.parse(filesystem.geturl(outer_path.as_posix()))
            assert base_url is not None
            super().__init__(
                tile_shape=tile_shape,
                interval=Shape5D.create(raw_shape=self._dataset.shape, axiskeys=self.axiskeys).to_interval5d(location),
                dtype=self._dataset.dtype,
                spatial_resolution=spatial_resolution or (1,1,1), # FIXME
                filesystem=filesystem,
                path=self.outer_path
            )
        except Exception as e:
            f.close()
            raise e

    @property
    def url(self) -> Url:
        url = Url.parse(self.filesystem.geturl(self.outer_path.as_posix()))
        assert url is not None
        return url.updated_with(hash_=f"inner_path={self.inner_path.as_posix()}")

    def __hash__(self) -> int:
        return super().__hash__()

    def __eq__(self, other: object) -> bool:
        return super().__eq__(other)

    def to_json_value(self) -> JsonObject:
        return {**super().to_json_value(), "outer_path": self.outer_path.as_posix(), "inner_path": self.inner_path.as_posix()}

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "H5DataSource":
        value_obj = ensureJsonObject(value)
        return H5DataSource(
            outer_path=PurePosixPath(ensureJsonString(value_obj.get("outer_path"))),
            inner_path=PurePosixPath(ensureJsonString(value_obj.get("inner_path"))),
            filesystem=JsonableFilesystem.from_json_value(value_obj.get("filesystem")),
            location=ensureOptional(Point5D.from_json_value, value_obj.get("location")) or Point5D.zero(),
            spatial_resolution=ensureJsonIntTripplet(value_obj.get("spatial_resolution"))
        )

    def _get_tile(self, tile: Interval5D) -> Array5D:
        slices = tile.translated(-self.location).to_slices(self.axiskeys)
        raw: np.ndarray = self._dataset[slices]
        return Array5D(raw, axiskeys=self.axiskeys, location=tile.start)

    def close(self) -> None:
        self._dataset.file.close()

    @classmethod
    def getAxisKeys(cls, dataset: h5py.Dataset) -> str:
        dims_axiskeys = "".join([dim.label for dim in dataset.dims]) # type: ignore
        if len(dims_axiskeys) != 0:
            if len(dims_axiskeys) != len(dataset.shape):
                raise ValueError("Axiskeys from 'dims' is inconsistent with shape: {dims_axiskeys} {dataset.shape}")
            return dims_axiskeys

        if "axistags" in dataset.attrs:
            tag_dict = json.loads(cast(str, dataset.attrs["axistags"]))
            return "".join(tag["key"] for tag in tag_dict["axes"])

        return guess_axiskeys(dataset.shape)

FsDataSource.datasource_from_json_constructors[H5DataSource.__name__] = H5DataSource.from_json_value
