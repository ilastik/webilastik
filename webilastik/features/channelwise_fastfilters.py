from abc import abstractmethod
from typing import Any, Literal, Optional, TypeVar, Type, List
import fastfilters #type: ignore
import math

import numpy
from numpy import ndarray, float32, dtype
from ndstructs.array5D import All, Array5D
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString, ensureJsonFloat
from ndstructs.point5D import Point5D, Shape5D

from .feature_extractor import FeatureData, FeatureExtractor, JsonableFeatureExtractor
from webilastik.datasource import DataSource, DataRoi
from webilastik.operator import Operator, OpRetriever
from global_cache import global_cache

Axis2D = Literal["x", "y", "z"]

def get_axis_2d(data: JsonValue) -> Optional[Axis2D]:
    axis_2d = ensureJsonString(data)
    if len(axis_2d) != 1 or axis_2d not in ("x", "y", "z"):
        raise ValueError(f"Bad value for axis_2d in {data}")
    return axis_2d


WINDOW_SIZE = 3.5

class PresmoothedFilter(FeatureExtractor):
    def __init__(
        self,
        *,
        ilp_scale: float,
        axis_2d: Optional[Axis2D],
        preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx"),
    ):
        self.ilp_scale = ilp_scale
        self.presmoother = GaussianSmoothing(
            preprocessor=preprocessor,
            axis_2d=axis_2d,
            window_size=WINDOW_SIZE,
            sigma=math.sqrt(ilp_scale ** 2 - 1.0) if ilp_scale > 1.0 else ilp_scale,
        )
        self.ilp_scale = ilp_scale
        self.axis_2d = axis_2d
        super().__init__()

class ChannelwiseFastFilter(JsonableFeatureExtractor):
    def __init__(
        self,
        *,
        preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx"),
        axis_2d: Optional[Axis2D],
    ):
        super().__init__()
        self.preprocessor = preprocessor
        self.axis_2d=axis_2d

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": self.__class__.__name__,
            "axis_2d": self.axis_2d,
        }

    @abstractmethod
    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        pass

    @property
    @abstractmethod
    def channel_multiplier(self) -> int:
        pass

    def __repr__(self):
        props = " ".join(f"{k}={v}" for k, v in self.__dict__.items())
        return f"<{self.__class__.__name__} {props}>"

    @property
    def halo(self) -> Point5D:
        # FIXME: Add appropriate halo property to filters
        args = {"x": 30, "y": 30, "z": 30, "c": 0}
        if self.axis_2d:
            args[self.axis_2d] = 0
        return Point5D(**args)

    def is_applicable_to(self, datasource: DataSource) -> bool:
        return datasource.shape >= self.halo * 2

    @global_cache
    def __call__(self, roi: DataRoi) -> FeatureData:
        haloed_roi = roi.enlarged(self.halo)
        source_data = self.preprocessor(haloed_roi)

        step_shape: Shape5D = Shape5D(
            c=1,
            t=1,
            x= 1 if self.axis_2d == "x" else source_data.shape.x,
            y= 1 if self.axis_2d == "y" else source_data.shape.y,
            z= 1 if self.axis_2d == "z" else source_data.shape.z,
        )

        out = Array5D.allocate(
            interval=roi.updated(
                c=(roi.c[0] * self.channel_multiplier, roi.c[1] * self.channel_multiplier)
            ),
            dtype=numpy.dtype("float32"),
            axiskeys=source_data.axiskeys.replace("c", "") + "c" # fastfilters puts channel last
        )

        for data_slice in source_data.split(step_shape):
            source_axes = "zyx"
            if self.axis_2d:
                source_axes = source_axes.replace(self.axis_2d, "")

            raw_data: "ndarray[Any, dtype[float32]]" = data_slice.raw(source_axes).astype(numpy.float32)
            raw_feature_data: "ndarray[Any, dtype[float32]]" = self.filter_fn(raw_data)

            feature_data = FeatureData(
                raw_feature_data,
                axiskeys=source_axes + "c" if len(raw_feature_data.shape) > len(source_axes) else source_axes,
                location=data_slice.location.updated(c=data_slice.location.c * self.channel_multiplier)
            )
            out.set(feature_data, autocrop=True)
        out.setflags(write=False)
        return FeatureData(
            out.raw(out.axiskeys),
            axiskeys=out.axiskeys,
            location=out.location,
        )


class StructureTensorEigenvalues(ChannelwiseFastFilter):
    def __init__(
        self,
        *,
        preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx"),
        innerScale: float,
        outerScale: float,
        window_size: float = 0,
        axis_2d: Optional[Axis2D],
    ):
        super().__init__(preprocessor=preprocessor, axis_2d=axis_2d)
        self.innerScale = innerScale
        self.outerScale = outerScale
        self.window_size = window_size

    @classmethod
    def from_json_value(cls, data: JsonValue) -> "StructureTensorEigenvalues":
        data_dict = ensureJsonObject(data)
        return cls(
            innerScale=ensureJsonFloat(data_dict.get("innerScale")),
            outerScale=ensureJsonFloat(data_dict.get("outerScale")),
            window_size=ensureJsonFloat(data_dict.get("window_size", 0)),
            axis_2d=get_axis_2d(data_dict.get("axis_2d")),
        )

    def to_json_value(self) -> JsonObject:
        return {
            **super().to_json_value(),
            "innerScale": self.innerScale,
            "outerScale": self.outerScale,
            "window_size": self.window_size,
        }

    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        return fastfilters.structureTensorEigenvalues(
            source_raw, innerScale=self.innerScale, outerScale=self.outerScale, window_size=self.window_size
        )

    @property
    def channel_multiplier(self) -> int:
        return 2 if self.axis_2d else 3

    @classmethod
    def from_ilp_scale(
        cls, *, preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx"), scale: float, axis_2d: Optional[Axis2D]
    ) -> "StructureTensorEigenvalues":
        capped_scale = min(scale, 1.0)
        return cls(
            preprocessor=preprocessor,
            innerScale=capped_scale,
            outerScale=0.5 * capped_scale,
            axis_2d=axis_2d,
        )


SIGMA_FILTER = TypeVar("SIGMA_FILTER", bound="SigmaWindowFilter")


class SigmaWindowFilter(ChannelwiseFastFilter):
    def __init__(
        self,
        *,
        preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx"),
        sigma: float,
        window_size: float = 0,
        axis_2d: Optional[Axis2D],
    ):
        super().__init__(preprocessor=preprocessor, axis_2d=axis_2d)
        self.sigma = sigma
        self.window_size = window_size

    @classmethod
    def from_json_value(cls: Type[SIGMA_FILTER], data: JsonValue) -> SIGMA_FILTER:
        data_dict = ensureJsonObject(data)
        return cls(
            sigma=ensureJsonFloat(data_dict.get("sigma")),
            window_size=ensureJsonFloat(data_dict.get("window_size", 0)),
            axis_2d=get_axis_2d(data_dict.get("axis_2d")),
        )

    def to_json_value(self) -> JsonObject:
        return {
            **super().to_json_value(),
            "sigma": self.sigma,
            "window_size": self.window_size,
        }

    @classmethod
    def from_ilp_scale(
        cls: Type[SIGMA_FILTER],
        *,
        preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx"),
        scale: float,
        axis_2d: Optional[Axis2D]
    ) -> SIGMA_FILTER:
        return cls(
            preprocessor=preprocessor,
            sigma=min(scale, 1.0),
            axis_2d=axis_2d,
        )


class GaussianGradientMagnitude(SigmaWindowFilter):
    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        return fastfilters.gaussianGradientMagnitude(source_raw, sigma=self.sigma, window_size=self.window_size)

    @property
    def channel_multiplier(self) -> int:
        return 1

class GaussianSmoothing(SigmaWindowFilter):
    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        return fastfilters.gaussianSmoothing(source_raw, sigma=self.sigma, window_size=self.window_size)

    @property
    def channel_multiplier(self) -> int:
        return 1


class DifferenceOfGaussians(ChannelwiseFastFilter):
    def __init__(
        self,
        *,
        preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx"),
        sigma0: float,
        sigma1: float,
        window_size: float = 0,
        axis_2d: Optional[Axis2D],
    ):
        super().__init__(preprocessor=preprocessor, axis_2d=axis_2d)
        self.sigma0 = sigma0
        self.sigma1 = sigma1
        self.window_size = window_size

    @property
    def channel_multiplier(self) -> int:
        return 1

    @classmethod
    def from_json_value(cls, data: JsonValue) -> "DifferenceOfGaussians":
        data_dict = ensureJsonObject(data)
        return cls(
            sigma0=ensureJsonFloat(data_dict.get("sigma0")),
            sigma1=ensureJsonFloat(data_dict.get("sigma1")),
            window_size=ensureJsonFloat(data_dict.get("window_size", 0)),
            axis_2d=get_axis_2d(data_dict.get("axis_2d")),
        )

    def to_json_value(self) -> JsonObject:
        return {
            **super().to_json_value(),
            "sigma0": self.sigma0,
            "sigma1": self.sigma1,
            "window_size": self.window_size,
        }

    def __repr__(self):
        return f"<{self.__class__.__name__} sigma0:{self.sigma0} sigma1:{self.sigma1} window_size:{self.window_size} axis_2d:{self.axis_2d}>"

    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        a = fastfilters.gaussianSmoothing(source_raw, sigma=self.sigma0, window_size=self.window_size)
        b = fastfilters.gaussianSmoothing(source_raw, sigma=self.sigma1, window_size=self.window_size)
        return a - b


ScaleFilter = TypeVar("ScaleFilter", bound="ScaleWindowFilter")


class ScaleWindowFilter(ChannelwiseFastFilter):
    def __init__(
        self,
        *,
        preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx"),
        scale: float,
        window_size: float = 0,
        axis_2d: Optional[Axis2D],
    ):
        super().__init__(preprocessor=preprocessor, axis_2d=axis_2d)
        self.scale = scale
        self.window_size = window_size

    @classmethod
    def from_json_value(cls: Type[ScaleFilter], data: JsonValue) -> ScaleFilter:
        data_dict = ensureJsonObject(data)
        return cls(
            scale=ensureJsonFloat(data_dict.get("scale")),
            window_size=ensureJsonFloat(data_dict.get("window_size", 0)),
            axis_2d=get_axis_2d(data_dict.get("axis_2d")),
        )

    def to_json_value(self) -> JsonObject:
        return {
            **super().to_json_value(),
            "scale": self.scale,
            "window_size": self.window_size,
        }


class HessianOfGaussianEigenvalues(ScaleWindowFilter):
    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        return fastfilters.hessianOfGaussianEigenvalues(source_raw, scale=self.scale, window_size=self.window_size)

    @property
    def channel_multiplier(self) -> int:
        return 2 if self.axis_2d else 3


class LaplacianOfGaussian(ScaleWindowFilter):
    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        return fastfilters.laplacianOfGaussian(source_raw, scale=self.scale, window_size=self.window_size)

    @property
    def channel_multiplier(self) -> int:
        return 1
