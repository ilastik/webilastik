from abc import abstractmethod
from typing import Any, Optional, TypeVar, Type, List
import math
import fastfilters #type: ignore

import numpy
from numpy import ndarray, float32, dtype
from ndstructs.array5D import All, Array5D
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString, ensureJsonFloat
from ndstructs.point5D import Point5D, Shape5D

from .feature_extractor import FeatureData
from .ilp_filter import IlpFilter
from webilastik.datasource import DataSource, DataRoi
from webilastik.operator import Operator, OpRetriever
from global_cache import global_cache


def get_axis_2d(data: JsonValue) -> Optional[str]:
    data_dict = ensureJsonObject(data)
    axis_2d = data_dict.get("axis_2d")
    if axis_2d is None:
        return None
    axis_2d = ensureJsonString(axis_2d)
    if len(axis_2d) != 1 or axis_2d not in Point5D.LABELS:
        raise ValueError(f"Bad value for axis_2d in {data}")
    return axis_2d


class ChannelwiseFastFilter(IlpFilter):
    def __init__(
        self,
        *,
        preprocessor: Operator[DataRoi, Array5D] = OpRetriever(),
        axis_2d: Optional[str] = None,
        presmooth_sigma: float = 0
    ):
        self.preprocessor = preprocessor
        self.presmooth_sigma = presmooth_sigma
        super().__init__(axis_2d=axis_2d)

    def to_json_data(self) -> JsonObject:
        return {
            "__class__": self.__class__.__name__,
            "axis_2d": self.axis_2d,
            "presmooth_sigma": self.presmooth_sigma,
        }

    @abstractmethod
    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        pass

    @classmethod
    def calc_presmooth_sigma(cls, scale: float) -> float:
        if scale > 1.0:
            return math.sqrt(scale ** 2 - 1.0)
        else:
            return scale

    def get_ilp_scale(self, capped_scale: float) -> float:
        if capped_scale < 1:
            return capped_scale
        if self.presmooth_sigma == 1.0:
            return 1.0
        # presmooth_sigma = math.sqrt(ilp_scale ** 2 - 1.0)
        # presmooth_sigma ** 2 = ilp_scale ** 2 - 1.0
        # presmooth_sigma ** 2 + 1 = ilp_scale ** 2
        # math.sqrt(presmooth_sigma ** 2 + 1) = ilp_scale
        return numpy.around(math.sqrt(self.presmooth_sigma ** 2 + 1), decimals=2)

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
    def __call__(self, /, roi: DataRoi) -> FeatureData:
        roi_step: Shape5D = roi.shape.updated(c=1, t=1)  # compute features independently for each c and each t
        if self.axis_2d:
            roi_step = roi_step.updated(**{self.axis_2d: 1})  # also compute in 2D slices

        per_channel_results : List[FeatureData] = []
        for roi_slice in roi.split(roi_step):
            haloed_roi = roi_slice.enlarged(self.halo)
            channel_offset = roi_slice.start.c - roi.start.c
            if self.presmooth_sigma > 0:
                gaussian_filter = GaussianSmoothing(
                    preprocessor=self.preprocessor, sigma=self.presmooth_sigma, axis_2d=self.axis_2d, window_size=3.5
                )
                source_data = gaussian_filter(haloed_roi)
            else:
                source_data = self.preprocessor(haloed_roi)

            source_axes = "zyx"
            if self.axis_2d:
                source_axes = source_axes.replace(self.axis_2d, "")

            raw_data: "ndarray[Any, dtype[float32]]" = source_data.raw(source_axes).astype(numpy.float32)
            raw_feature_data: "ndarray[Any, dtype[float32]]" = self.filter_fn(raw_data)
            if len(raw_feature_data.shape) > len(source_axes):
                output_axes = source_axes + "c"
                channel_multiplier = raw_feature_data.shape[-1]
            else:
                output_axes = source_axes
                channel_multiplier = 1
            feature_data = FeatureData(
                raw_feature_data,
                axiskeys=output_axes,
                location=haloed_roi.start.updated(c=channel_offset * channel_multiplier)
            )
            per_channel_results.append(feature_data.cut(roi_slice, c=All()))
        combined_result = Array5D.combine(per_channel_results)
        out = FeatureData(
            combined_result.raw(combined_result.axiskeys), axiskeys=combined_result.axiskeys, location=combined_result.location
        )
        out.setflags(write=False)
        return out

class StructureTensorEigenvalues(ChannelwiseFastFilter):
    def __init__(
        self,
        *,
        preprocessor: Operator[DataRoi, Array5D] = OpRetriever(),
        innerScale: float,
        outerScale: float,
        window_size: float = 0,
        axis_2d: Optional[str] = None,
        presmooth_sigma: float = 0,
    ):
        super().__init__(
            preprocessor=preprocessor, axis_2d=axis_2d, presmooth_sigma=presmooth_sigma
        )
        self.innerScale = innerScale
        self.outerScale = outerScale
        self.window_size = window_size

    @classmethod
    def from_json_data(cls, data: JsonValue) -> "StructureTensorEigenvalues":
        data_dict = ensureJsonObject(data)
        return cls(
            innerScale=ensureJsonFloat(data_dict.get("innerScale")),
            outerScale=ensureJsonFloat(data_dict.get("outerScale")),
            window_size=ensureJsonFloat(data_dict.get("window_size", 0)),
            axis_2d=get_axis_2d(data),
            presmooth_sigma=ensureJsonFloat(data_dict.get("presmooth_sigma", 0)),
        )

    def to_json_data(self) -> JsonObject:
        return {
            **super().to_json_data(),
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
        cls, *, preprocessor: Operator[DataRoi, Array5D] = OpRetriever(), scale: float, axis_2d: Optional[str] = None
    ) -> "StructureTensorEigenvalues":
        capped_scale = min(scale, 1.0)
        return cls(
            preprocessor=preprocessor,
            innerScale=capped_scale,
            outerScale=0.5 * capped_scale,
            axis_2d=axis_2d,
            presmooth_sigma=cls.calc_presmooth_sigma(scale),
        )

    @property
    def ilp_scale(self) -> float:
        return self.get_ilp_scale(self.innerScale)


SIGMA_FILTER = TypeVar("SIGMA_FILTER", bound="SigmaWindowFilter")


class SigmaWindowFilter(ChannelwiseFastFilter):
    def __init__(
        self,
        *,
        preprocessor: Operator[DataRoi, Array5D] = OpRetriever(),
        sigma: float,
        window_size: float = 0,
        axis_2d: Optional[str] = None,
        presmooth_sigma: float = 0,
    ):
        super().__init__(axis_2d=axis_2d, presmooth_sigma=presmooth_sigma)
        self.sigma = sigma
        self.window_size = window_size

    @classmethod
    def from_json_data(cls: Type[SIGMA_FILTER], data: JsonValue) -> SIGMA_FILTER:
        data_dict = ensureJsonObject(data)
        return cls(
            sigma=ensureJsonFloat(data_dict.get("sigma")),
            window_size=ensureJsonFloat(data_dict.get("window_size", 0)),
            axis_2d=get_axis_2d(data),
            presmooth_sigma=ensureJsonFloat(data_dict.get("presmooth_sigma", 0)),
        )

    def to_json_data(self) -> JsonObject:
        return {
            **super().to_json_data(),
            "sigma": self.sigma,
            "window_size": self.window_size,
        }

    @classmethod
    def from_ilp_scale(
        cls: Type[SIGMA_FILTER], *, preprocessor: Operator[DataRoi, Array5D] = OpRetriever(), scale: float, axis_2d: Optional[str] = None
    ) -> SIGMA_FILTER:
        return cls(
            preprocessor=preprocessor,
            sigma=min(scale, 1.0),
            axis_2d=axis_2d,
            presmooth_sigma=cls.calc_presmooth_sigma(scale),
        )

    @property
    def ilp_scale(self) -> float:
        return self.get_ilp_scale(self.sigma)


class GaussianGradientMagnitude(SigmaWindowFilter):
    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        return fastfilters.gaussianGradientMagnitude(source_raw, sigma=self.sigma, window_size=self.window_size)


class GaussianSmoothing(SigmaWindowFilter):
    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        return fastfilters.gaussianSmoothing(source_raw, sigma=self.sigma, window_size=self.window_size)


class DifferenceOfGaussians(ChannelwiseFastFilter):
    def __init__(
        self,
        *,
        preprocessor: Operator[DataRoi, Array5D] = OpRetriever(),
        sigma0: float,
        sigma1: float,
        window_size: float = 0,
        axis_2d: Optional[str] = None,
        presmooth_sigma: float = 0,
    ):
        super().__init__(
            preprocessor=preprocessor, axis_2d=axis_2d, presmooth_sigma=presmooth_sigma
        )
        self.sigma0 = sigma0
        self.sigma1 = sigma1
        self.window_size = window_size

    @classmethod
    def from_json_data(cls, data: JsonValue) -> "DifferenceOfGaussians":
        data_dict = ensureJsonObject(data)
        return cls(
            sigma0=ensureJsonFloat(data_dict.get("sigma0")),
            sigma1=ensureJsonFloat(data_dict.get("sigma1")),
            window_size=ensureJsonFloat(data_dict.get("window_size", 0)),
            axis_2d=get_axis_2d(data),
            presmooth_sigma=ensureJsonFloat(data_dict.get("presmooth_sigma", 0)),
        )

    def to_json_data(self) -> JsonObject:
        return {
            **super().to_json_data(),
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

    @classmethod
    def from_ilp_scale(
        cls, *, preprocessor: Operator[DataRoi, Array5D] = OpRetriever(), scale: float, axis_2d: Optional[str] = None
    ) -> "DifferenceOfGaussians":
        capped_scale = min(scale, 1.0)
        return cls(
            preprocessor=preprocessor,
            sigma0=capped_scale,
            sigma1=capped_scale * 0.66,
            axis_2d=axis_2d,
            presmooth_sigma=cls.calc_presmooth_sigma(scale),
        )

    @property
    def ilp_scale(self) -> float:
        return self.get_ilp_scale(self.sigma0)


ScaleFilter = TypeVar("ScaleFilter", bound="ScaleWindowFilter")


class ScaleWindowFilter(ChannelwiseFastFilter):
    def __init__(
        self,
        *,
        preprocessor: Operator[DataRoi, Array5D] = OpRetriever(),
        scale: float,
        window_size: float = 0,
        axis_2d: Optional[str] = None,
        presmooth_sigma: float = 0,
    ):
        super().__init__(
            preprocessor=preprocessor, axis_2d=axis_2d, presmooth_sigma=presmooth_sigma
        )
        self.scale = scale
        self.window_size = window_size

    @classmethod
    def from_json_data(cls: Type[ScaleFilter], data: JsonValue) -> ScaleFilter:
        data_dict = ensureJsonObject(data)
        return cls(
            scale=ensureJsonFloat(data_dict.get("scale")),
            window_size=ensureJsonFloat(data_dict.get("window_size", 0)),
            axis_2d=get_axis_2d(data),
            presmooth_sigma=ensureJsonFloat(data_dict.get("presmooth_sigma", 0)),
        )

    def to_json_data(self) -> JsonObject:
        return {
            **super().to_json_data(),
            "scale": self.scale,
            "window_size": self.window_size,
        }

    @classmethod
    def from_ilp_scale(
        cls: Type[ScaleFilter], *, preprocessor: Operator[DataRoi, Array5D] = OpRetriever(), scale: float, axis_2d: Optional[str] = None
    ) -> ScaleFilter:
        return cls(
            preprocessor=preprocessor,
            scale=min(scale, 1.0),
            axis_2d=axis_2d,
            presmooth_sigma=cls.calc_presmooth_sigma(scale),
        )

    @property
    def ilp_scale(self) -> float:
        return self.get_ilp_scale(self.scale)


class HessianOfGaussianEigenvalues(ScaleWindowFilter):
    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        return fastfilters.hessianOfGaussianEigenvalues(source_raw, scale=self.scale, window_size=self.window_size)

    @property
    def channel_multiplier(self) -> int:
        return 2 if self.axis_2d else 3


class LaplacianOfGaussian(ScaleWindowFilter):
    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        return fastfilters.laplacianOfGaussian(source_raw, scale=self.scale, window_size=self.window_size)
