from abc import abstractmethod
from dataclasses import dataclass
from itertools import combinations_with_replacement
from typing import Optional, TypeVar, Type, cast, List
import math
import fastfilters
from ndstructs.array5D import All

import numpy

from .feature_extractor import FeatureData
from .ilp_filter import IlpFilter, OpRetriever
from webilastik.operator import Operator
from ndstructs import Array5D, Image, ScalarImage
from ndstructs import Point5D, Interval5D, Shape5D
from ndstructs.datasource import DataSource, DataRoi
from ndstructs.utils import from_json_data, Dereferencer

try:
    import ilastik_operator_cache
    operator_cache = ilastik_operator_cache
except ImportError:
    from functools import lru_cache
    operator_cache = lru_cache()


CFF = TypeVar("CFF", bound="ChannelwiseFastFilter")

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

    @abstractmethod
    def filter_fn(self, source_raw: numpy.ndarray) -> numpy.ndarray:
        pass

    @classmethod
    def from_json_data(cls: Type[CFF], data, dereferencer: Optional[Dereferencer] = None) -> CFF:
        return cast(cls, from_json_data(cls, data, dereferencer=dereferencer, initOnly=True))

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

    @operator_cache # type: ignore
    def compute(self, roi: DataRoi) -> FeatureData:
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
                source_data = gaussian_filter.compute(haloed_roi)
            else:
                source_data = self.preprocessor.compute(haloed_roi)

            source_axes = "zyx"
            if self.axis_2d:
                source_axes = source_axes.replace(self.axis_2d, "")

            raw_data: numpy.ndarray = source_data.raw(source_axes).astype(numpy.float32)
            raw_feature_data: numpy.ndarray = self.filter_fn(raw_data)
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
        combined_result = per_channel_results[0].combine(per_channel_results[1:])
        combined_result.setflags(write=False)
        return combined_result

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

    def filter_fn(self, source_raw: numpy.ndarray) -> numpy.ndarray:
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


IlpFilter.REGISTRY[StructureTensorEigenvalues.__name__] = StructureTensorEigenvalues


SigmaFilter = TypeVar("SigmaFilter", bound="SigmaWindowFilter")


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
    def from_ilp_scale(
        cls: Type[SigmaFilter], *, preprocessor: Operator[DataRoi, Array5D] = OpRetriever(), scale: float, axis_2d: Optional[str] = None
    ) -> SigmaFilter:
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
    def filter_fn(self, source_raw: numpy.ndarray) -> numpy.ndarray:
        return fastfilters.gaussianGradientMagnitude(source_raw, sigma=self.sigma, window_size=self.window_size)


IlpFilter.REGISTRY[GaussianGradientMagnitude.__name__] = GaussianGradientMagnitude


class GaussianSmoothing(SigmaWindowFilter):
    def filter_fn(self, source_raw: numpy.ndarray) -> numpy.ndarray:
        return fastfilters.gaussianSmoothing(source_raw, sigma=self.sigma, window_size=self.window_size)


IlpFilter.REGISTRY[GaussianSmoothing.__name__] = GaussianSmoothing


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

    def __repr__(self):
        return f"<{self.__class__.__name__} sigma0:{self.sigma0} sigma1:{self.sigma1} window_size:{self.window_size} axis_2d:{self.axis_2d}>"

    def filter_fn(self, source_raw: numpy.ndarray) -> numpy.ndarray:
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


IlpFilter.REGISTRY[DifferenceOfGaussians.__name__] = DifferenceOfGaussians


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
    def filter_fn(self, source_raw: numpy.ndarray) -> numpy.ndarray:
        return fastfilters.hessianOfGaussianEigenvalues(source_raw, scale=self.scale, window_size=self.window_size)

    @property
    def channel_multiplier(self) -> int:
        return 2 if self.axis_2d else 3


IlpFilter.REGISTRY[HessianOfGaussianEigenvalues.__name__] = HessianOfGaussianEigenvalues


class LaplacianOfGaussian(ScaleWindowFilter):
    def filter_fn(self, source_raw: numpy.ndarray) -> numpy.ndarray:
        return fastfilters.laplacianOfGaussian(source_raw, scale=self.scale, window_size=self.window_size)


IlpFilter.REGISTRY[LaplacianOfGaussian.__name__] = LaplacianOfGaussian
