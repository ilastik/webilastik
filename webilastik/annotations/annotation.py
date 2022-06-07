from typing import List, Sequence, Mapping, Tuple, Dict, Iterable, Sequence, Any, Optional
import itertools

import numpy as np
from ndstructs.point5D import Interval5D, Point5D, Shape5D
from ndstructs.array5D import Array5D, All, ScalarData, StaticLine
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonArray, ensureJsonInt, ensureJsonObject, ensureJsonString

from webilastik.datasource import DataSource, DataRoi, FsDataSource
from webilastik.features.feature_extractor import FeatureExtractor, FeatureData


class Color:
    def __init__(
        self,
        r: np.uint8 = np.uint8(0),
        g: np.uint8 = np.uint8(0),
        b: np.uint8 = np.uint8(0),
        name: str = "",
    ):
        self.r = r
        self.g = g
        self.b = b
        self.name = name or f"Label {self.rgba}"
        self.hex_code = f"#{r:02X}{g:02X}{b:02X}"
        super().__init__()

    @classmethod
    def from_json_data(cls, data: JsonValue) -> "Color":
        data_dict = ensureJsonObject(data)
        return Color(
            r=np.uint8(ensureJsonInt(data_dict.get("r", 0))),
            g=np.uint8(ensureJsonInt(data_dict.get("g", 0))),
            b=np.uint8(ensureJsonInt(data_dict.get("b", 0))),
        )

    def to_json_data(self) -> JsonObject:
        return {
            "r": int(self.r),
            "g": int(self.g),
            "b": int(self.b),
        }

    @classmethod
    def from_channels(cls, channels: List[np.uint8], name: str = "") -> "Color":
        if len(channels) == 0 or len(channels) > 3:
            raise ValueError(f"Cannnot create color from {channels}")
        if len(channels) == 1:
            channels = [channels[0], channels[0], channels[0]]
        return cls(r=channels[0], g=channels[1], b=channels[2], name=name)

    @property
    def rgba(self) -> Tuple[np.uint8, np.uint8, np.uint8]:
        return (self.r, self.g, self.b)

    @property
    def q_rgba(self) -> int:
        return sum(c * (16 ** (3 - idx)) for idx, c in enumerate(self.rgba))

    @property
    def ilp_data(self) -> "np.ndarray[Any, Any]":
        return np.asarray(self.rgba, dtype=np.int64)

    def __hash__(self):
        return hash(self.rgba)

    def __eq__(self, other: object) -> bool:
        return not isinstance(other, Color) or self.rgba == other.rgba

    @classmethod
    def sort(cls, colors: Iterable["Color"]) -> List["Color"]:
        return sorted(colors, key=lambda c: c.q_rgba)

    @classmethod
    def create_color_map(cls, colors: Iterable["Color"]) -> Dict["Color", np.uint8]:
        return {color: np.uint8(idx + 1) for idx, color in enumerate(cls.sort(set(colors)))}

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} r={self.r} g={self.g} b={self.b}>"

class FeatureSamples(FeatureData, StaticLine):
    """A multi-channel array with a single spacial dimension, with each channel representing a feature calculated on
    top of an annotated pixel. Features are assumed to be relative to a single label (annotation color)"""

    @classmethod
    def create(cls, annotation: "Annotation", data: FeatureData):
        samples = data.sample_channels(annotation.as_mask()) #type: ignore
        return cls.fromArray5D(samples)

    @property
    def X(self) -> "np.ndarray[Any, Any]":
        return self.linear_raw()

    def get_y(self, label_class: np.uint8) -> "np.ndarray[Any, np.dtype[np.uint32]]":
        return np.full((self.shape.volume, 1), label_class, dtype=np.uint32)


class AnnotationOutOfBounds(Exception):
    def __init__(self, annotation_roi: Interval5D, raw_data: DataSource):
        super().__init__(f"Annotation roi {annotation_roi} exceeds bounds of raw_data {raw_data}")


class Annotation(ScalarData):
    """User annotation attached to the raw data onto which they were drawn"""

    def __hash__(self):
        return hash(self._data.tobytes())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Annotation):
            return False
        return self.interval == other.interval and bool(np.all(self._data == other._data))

    def __init__(
        self, arr: "np.ndarray[Any, Any]", *, axiskeys: str, location: Point5D = Point5D.zero(), raw_data: DataSource
    ):
        super().__init__(arr.astype(bool), axiskeys=axiskeys, location=location)
        if not raw_data.interval.contains(self.interval):
            raise AnnotationOutOfBounds(annotation_roi=self.interval, raw_data=raw_data)
        self.raw_data = raw_data

    def rebuild(self, arr: "np.ndarray[Any, Any]", *, axiskeys: str, location: "Point5D | None" = None) -> "Annotation":
        location = self.location if location is None else location
        return self.__class__(arr, axiskeys=axiskeys, location=location, raw_data=self.raw_data)

    @classmethod
    def interpolate_from_points(cls, voxels: Sequence[Point5D], raw_data: DataSource):
        start = Point5D.min_coords(voxels)
        stop = Point5D.max_coords(voxels) + 1  # +1 because slice.stop is exclusive, but max_point isinclusive
        scribbling_roi = Interval5D.create_from_start_stop(start=start, stop=stop)
        if scribbling_roi.shape.c != 1:
            raise ValueError(f"Annotations must not span multiple channels: {voxels}")
        scribblings = Array5D.allocate(scribbling_roi, dtype=np.dtype(bool), value=False)

        anchor = voxels[0]
        for voxel in voxels:
            for interp_voxel in anchor.interpolate_until(voxel):
                scribblings.paint_point(point=interp_voxel, value=True)
            anchor = voxel

        return cls(scribblings._data, axiskeys=scribblings.axiskeys, raw_data=raw_data, location=start)

    @classmethod
    def from_json_value(cls, data: JsonValue) -> "Annotation":
        data_dict = ensureJsonObject(data)
        raw_voxels = ensureJsonArray(data_dict.get("voxels"))
        voxels : Sequence[Point5D] = [Point5D.from_json_value(raw_voxel) for raw_voxel in raw_voxels]

        raw_data = DataSource.from_json_value(data_dict.get("raw_data"))

        return cls.from_voxels(voxels=voxels, raw_data=raw_data)

    @classmethod
    def from_voxels(cls, voxels: Sequence[Point5D], raw_data: DataSource) -> "Annotation":
        start = Point5D.min_coords(voxels)
        stop = Point5D.max_coords(voxels) + 1  # +1 because slice.stop is exclusive, but max_point isinclusive
        scribbling_roi = Interval5D.create_from_start_stop(start=start, stop=stop)
        if scribbling_roi.shape.c != 1:
            raise ValueError(f"Annotations must not span multiple channels: {voxels}")
        scribblings = Array5D.allocate(scribbling_roi, dtype=np.dtype(bool), value=False)

        for voxel in voxels:
            scribblings.paint_point(point=voxel, value=True)

        return cls(scribblings._data, axiskeys=scribblings.axiskeys, raw_data=raw_data, location=start)

    def to_points(self) -> Iterable[Point5D]:
        # FIXME: annotation should probably not be an Array6D
        for x, y, z in zip(*self.raw("xyz").nonzero()): # type: ignore
            yield Point5D(x=x, y=y, z=z) + self.location

    def to_json_data(self) -> JsonObject:
        if not isinstance(self.raw_data, FsDataSource):
            #FIXME: maybe create a FsDatasourceAnnotation so we don't have to raise here?
            raise ValueError(f"Can't serialize annotation over {self.raw_data}")

        return {
            "raw_data": self.raw_data.to_json_value(),
            "voxels": tuple(vx.to_json_value() for vx in self.to_points()),
        }

    def get_feature_samples(self, feature_extractor: FeatureExtractor) -> FeatureSamples:
        interval_under_annotation = self.interval.updated(c=self.raw_data.interval.c)

        def make_samples(data_tile: DataRoi) -> FeatureSamples:
            annotation_tile = self.clamped(data_tile)
            feature_tile = feature_extractor.compute(data_tile).cut(annotation_tile.interval, c=All())
            return FeatureSamples.create(annotation_tile, feature_tile)

        tile_shape = self.raw_data.tile_shape.updated(c=self.raw_data.shape.c)
        all_feature_samples = list(map(
            make_samples,
            self.raw_data.roi.clamped(interval_under_annotation).get_tiles(tile_shape=tile_shape, tiles_origin=self.raw_data.location)
        ))

        return all_feature_samples[0].concatenate(*all_feature_samples[1:])

    def colored(self, value: np.uint8) -> Array5D:
        return Array5D(self._data * value, axiskeys=self.axiskeys, location=self.location)

    def __repr__(self):
        return f"<Annotation {self.interval} onto {self.raw_data}>"

    def show(self, color: Color):
        background = self.raw_data.retrieve(self.interval.updated(c=self.raw_data.interval.c)).cut(copy=True)

        raw_background = background.raw("tzyxc")
        raw_annotation = self.raw("tzyx")
        raw_background[raw_annotation > 0] = [color.r, color.g, color.b]

        background.show_images()
