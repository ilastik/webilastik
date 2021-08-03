import json
import enum
from abc import abstractmethod, ABC
from enum import IntEnum
from pathlib import Path, PurePosixPath
from typing import Optional, Tuple, Union, cast, Iterator
from typing_extensions import Final

import h5py
import numpy as np
import skimage.io #type: ignore
from fs.base import FS

from ndstructs import Array5D, Shape5D, Interval5D, Point5D
from ndstructs.array5D import SPAN_OVERRIDE, All
from ndstructs.point5D import SPAN
from ndstructs.utils.json_serializable import JsonObject

try:
    import ndstructs_datasource_cache # type: ignore
except ImportError:
    from functools import lru_cache

    ndstructs_datasource_cache = lru_cache(maxsize=4096)


@enum.unique
class AddressMode(IntEnum):
    BLACK = 0

def guess_axiskeys(raw_shape: Tuple[int, ...]) -> str:
    guesses = {5: "tzyxc", 4: "zyxc", 3: "yxc", 2: "yx", 1: "x"}
    return guesses[len(raw_shape)]


class DataSource(ABC):
    tile_shape: Final[Shape5D]
    dtype: Final[np.dtype]
    interval: Final[Interval5D]
    shape: Final[Shape5D]
    location: Final[Point5D]
    axiskeys: Final[str]
    spatial_resolution: Final[Tuple[int, int, int]]
    roi: Final["DataRoi"]

    def __init__(
        self,
        *,
        tile_shape: Shape5D,
        dtype: np.dtype,
        interval: Interval5D,
        axiskeys: str,
        spatial_resolution: Tuple[int, int, int] = (1,1,1), # FIXME: experimental, like precomp chunks resolution
    ):
        self.tile_shape = tile_shape
        self.dtype = dtype
        self.interval = interval
        self.shape = interval.shape
        self.location = interval.start
        self.axiskeys = axiskeys
        self.spatial_resolution = spatial_resolution
        self.roi = DataRoi(self, **self.interval.to_dict())

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.interval}>"

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": self.__class__.__name__,
            "tile_shape": self.tile_shape.to_json_value(),
            "dtype": str(self.dtype.name),
            "interval": self.interval.to_json_value(),
            "axiskeys": self.axiskeys,
            "spatial_resolution": self.spatial_resolution,
        }

    @abstractmethod
    def __hash__(self) -> int:
        return hash((
            self.tile_shape,
            self.dtype,
            self.interval,
            self.axiskeys,
            self.spatial_resolution,
        ))

    @abstractmethod
    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__) and
            self.tile_shape == other.tile_shape and
            self.dtype == other.dtype and
            self.interval == other.interval and
            self.axiskeys == other.axiskeys and
            self.spatial_resolution == other.spatial_resolution
        )

    def is_tile(self, tile: Interval5D) -> bool:
        return tile.is_tile(tile_shape=self.tile_shape, full_interval=self.interval, clamped=True)

    @ndstructs_datasource_cache # type: ignore
    def get_tile(self, tile: Interval5D) -> Array5D:
        return self._get_tile(tile)

    @abstractmethod
    def _get_tile(self, tile: Interval5D) -> Array5D:
        pass

    def close(self) -> None:
        pass

    def _allocate(self, interval: Union[Shape5D, Interval5D], fill_value: int) -> Array5D:
        return Array5D.allocate(interval, dtype=self.dtype, value=fill_value)

    def retrieve(
        self,
        interval: Optional[Interval5D] = None,
        *,
        x: Optional[SPAN_OVERRIDE] = None,
        y: Optional[SPAN_OVERRIDE] = None,
        z: Optional[SPAN_OVERRIDE] = None,
        t: Optional[SPAN_OVERRIDE] = None,
        c: Optional[SPAN_OVERRIDE] = None,
        address_mode: AddressMode = AddressMode.BLACK,
    ) -> Array5D:
        interval = (interval or self.interval).updated(
            x=self.interval.x if isinstance(x, All) else x,
            y=self.interval.y if isinstance(y, All) else y,
            z=self.interval.z if isinstance(z, All) else z,
            t=self.interval.t if isinstance(t, All) else t,
            c=self.interval.c if isinstance(c, All) else c,
        )
        out = self._allocate(interval, fill_value=0)
        for tile in self.roi.clamped(interval).get_datasource_tiles(clamp_to_datasource=True):
            tile_data = self.get_tile(tile)
            out.set(tile_data, autocrop=True)
        out.setflags(write=False)
        return out


class DataRoi(Interval5D):
    datasource: Final[DataSource]

    def __init__(
        self,
        datasource: DataSource,
        *,
        t: Optional[SPAN] = None,
        c: Optional[SPAN] = None,
        x: Optional[SPAN] = None,
        y: Optional[SPAN] = None,
        z: Optional[SPAN] = None,
    ):
        super().__init__(
            t=t if t is not None else datasource.interval.t,
            c=c if c is not None else datasource.interval.c,
            x=x if x is not None else datasource.interval.x,
            y=y if y is not None else datasource.interval.y,
            z=z if z is not None else datasource.interval.z,
        )
        self.datasource = datasource

    def __hash__(self) -> int:
        return hash((super().__hash__(), self.datasource))

    def __eq__(self, other: object) -> bool:
        if not super().__eq__(other):
            return False
        if isinstance(other, DataRoi) and self.datasource != other.datasource:
            return False
        return True

    def updated(
        self,
        *,
        t: Optional[SPAN] = None,
        c: Optional[SPAN] = None,
        x: Optional[SPAN] = None,
        y: Optional[SPAN] = None,
        z: Optional[SPAN] = None,
    ) -> "DataRoi":
        inter = self.interval.updated(t=t, c=c, x=x, y=y, z=z)
        return self.__class__(datasource=self.datasource, x=inter.x, y=inter.y, z=inter.z, t=inter.t, c=inter.c)

    def __repr__(self) -> str:
        return f"<{super().__repr__()} of {self.datasource}>"

    def full(self) -> "DataRoi":
        return self.updated(**self.full_shape.to_interval5d().to_dict())

    @property
    def full_shape(self) -> Shape5D:
        return self.datasource.shape

    @property
    def tile_shape(self) -> Shape5D:
        return self.datasource.tile_shape

    @property
    def dtype(self):
        return self.datasource.dtype

    def is_datasource_tile(self) -> bool:
        return self.datasource.is_tile(self)

    @property
    def interval(self) -> Interval5D:
        return Interval5D(t=self.t, c=self.c, x=self.x, y=self.y, z=self.z)

    def retrieve(self, address_mode: AddressMode = AddressMode.BLACK) -> Array5D:
        return self.datasource.retrieve(self.interval, address_mode=address_mode)

    def default_split(self) -> Iterator["DataRoi"]:
        yield from super().split(self.tile_shape)

    def get_datasource_tiles(self, clamp_to_datasource: bool = True) -> Iterator["DataRoi"]:
        for tile in super().get_tiles(tile_shape=self.tile_shape, tiles_origin=self.datasource.location):
            if clamp_to_datasource:
                clamped = tile.clamped(self.datasource.interval)
                if clamped.shape.hypervolume == 0:
                    continue
                yield clamped
            else:
                yield tile

    # for this and the next method, tile_shape is needed because self could be an edge tile, and therefor
    # self.shape would not return a typical tile shape
    def get_neighboring_tiles(self, tile_shape: Shape5D) -> Iterator["DataRoi"]:
        for neighbor in super().get_neighboring_tiles(tile_shape):
            neighbor = neighbor.clamped(self.full())
            if neighbor.shape.hypervolume > 0 and neighbor != self:
                yield neighbor

    def get_neighbor_tile_adjacent_to(self, *, anchor: Interval5D, tile_shape: Shape5D) -> Optional["DataRoi"]:
        neighbor = super().get_neighbor_tile_adjacent_to(anchor=anchor, tile_shape=tile_shape)
        if neighbor is None:
            return None
        if not self.full().contains(neighbor):
            return None
        return neighbor.clamped(self.full())


class H5DataSource(DataSource):
    _dataset: h5py.Dataset
    def __init__(self, *, outer_path: Path, inner_path: PurePosixPath, location: Point5D = Point5D.zero(), filesystem: FS):
        self.outer_path = outer_path
        self.inner_path = inner_path
        self.filesystem = filesystem
        binfile = filesystem.openbin(outer_path.as_posix())
        f = h5py.File(binfile, "r")
        try:
            dataset = f[inner_path.as_posix()]
            if not isinstance(dataset, h5py.Dataset):
                raise ValueError(f"{inner_path} is not a Dataset")
            axiskeys = self.getAxisKeys(dataset)
            self._dataset = cast(h5py.Dataset, dataset)
            tile_shape = Shape5D.create(raw_shape=self._dataset.chunks or self._dataset.shape, axiskeys=axiskeys)
            super().__init__(
                tile_shape=tile_shape,
                interval=Shape5D.create(raw_shape=self._dataset.shape, axiskeys=axiskeys).to_interval5d(location),
                dtype=self._dataset.dtype,
                axiskeys=axiskeys,
            )
        except Exception as e:
            f.close()
            raise e

    def __hash__(self) -> int:
        return hash((
            super().__hash__(),
            self.filesystem.desc(self.outer_path.as_posix()),
            self.inner_path,
        ))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, H5DataSource) and
            super().__eq__(other) and
            self.filesystem.desc(self.outer_path.as_posix()) == other.filesystem.desc(other.outer_path.as_posix()) and
            self.inner_path == other.inner_path
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


class ArrayDataSource(DataSource):
    """A DataSource backed by an Array5D"""

    def __init__(
        self,
        *,
        data: np.ndarray,
        axiskeys: str,
        tile_shape: Optional[Shape5D] = None,
        location: Point5D = Point5D.zero(),
    ):
        self._data = Array5D(data, axiskeys=axiskeys, location=location)
        if tile_shape is None:
            tile_shape = Shape5D.hypercube(256).to_interval5d().clamped(self._data.shape).shape
        super().__init__(
            dtype=self._data.dtype,
            tile_shape=tile_shape,
            interval=self._data.interval,
            axiskeys=axiskeys,
        )

    def __hash__(self) -> int:
        return hash((self._data, self.tile_shape))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ArrayDataSource) and
            super().__eq__(other) and
            self._data == other._data
        )

    @classmethod
    def from_array5d(cls, arr: Array5D, *, tile_shape: Optional[Shape5D] = None, location: Point5D = Point5D.zero()):
        return cls(data=arr.raw(Point5D.LABELS), axiskeys=Point5D.LABELS, location=location, tile_shape=tile_shape)

    def _get_tile(self, tile: Interval5D) -> Array5D:
        return self._data.cut(tile, copy=True)

    def _allocate(self, interval: Union[Shape5D, Interval5D], fill_value: int) -> Array5D:
        return self._data.__class__.allocate(interval, dtype=self.dtype, value=fill_value)


class SkimageDataSource(ArrayDataSource):
    """A naive implementation of DataSource that can read images using skimage"""

    def __init__(
        self, path: Path, *, location: Point5D = Point5D.zero(), filesystem: FS, tile_shape: Optional[Shape5D] = None
    ):
        raw_data: np.ndarray = skimage.io.imread(filesystem.openbin(path.as_posix())) # type: ignore
        axiskeys = "yxc"[: len(raw_data.shape)]
        super().__init__(
            data=raw_data,
            axiskeys=axiskeys,
            location=location,
            tile_shape=tile_shape,
        )
