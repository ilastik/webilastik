# pyright: strict

from abc import ABC, abstractmethod
from typing import Any, Literal, Optional
import fastfilters #type: ignore
import math

import numpy
from numpy import ndarray, float32, dtype
from ndstructs.array5D import Array5D
from ndstructs.point5D import Point5D, Shape5D

from .feature_extractor import FeatureData, FeatureExtractor
from webilastik.datasource import DataSource, DataRoi
from webilastik.operator import OpRetriever, Preprocessor, preprocessor_from_dto
from webilastik.server.rpc.dto import (
    DifferenceOfGaussiansDto,
    GaussianGradientMagnitudeDto,
    GaussianSmoothingDto,
    HessianOfGaussianEigenvaluesDto,
    LaplacianOfGaussianDto,
    PreprocessorDto,
    StructureTensorEigenvaluesDto
)

from global_cache import global_cache

Axis2D = Literal["x", "y", "z"]

WINDOW_SIZE = 3.5

class PresmoothedFilter(ABC, FeatureExtractor):
    def __init__(
        self,
        *,
        ilp_scale: float,
        axis_2d: Optional[Axis2D],
        preprocessor: Preprocessor = OpRetriever(axiskeys_hint="ctzyx"),
        channel_index: int,
    ):
        self.ilp_scale = ilp_scale
        self.presmoother = GaussianSmoothing(
            preprocessor=preprocessor,
            axis_2d=axis_2d,
            window_size=WINDOW_SIZE,
            sigma=math.sqrt(ilp_scale ** 2 - 1.0) if ilp_scale > 1.0 else ilp_scale,
            channel_index=channel_index,
        )
        self.ilp_scale = ilp_scale
        self.axis_2d: Optional[Axis2D] = axis_2d
        super().__init__()

    @abstractmethod
    def to_dto(self) -> PreprocessorDto:
        pass

    @abstractmethod
    def is_applicable_to(self, datasource: DataSource) -> bool:
        pass

    @abstractmethod
    def __call__(self, roi: DataRoi) -> Array5D:
        pass

class FastFilter:
    def __init__(
        self,
        *,
        preprocessor: Optional[Preprocessor] = None,
        axis_2d: Optional[Axis2D],
        channel_index: int,
    ):
        super().__init__()
        self.preprocessor: Preprocessor = preprocessor if preprocessor is not None else OpRetriever(axiskeys_hint="ctzyx")
        self.axis_2d: Optional[Axis2D] = axis_2d
        self.channel_index = channel_index

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
        return datasource.shape >= self.halo * 2 and (datasource.interval.c[0] <= self.channel_index < datasource.interval.c[1])

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
                c=(self.channel_index * self.channel_multiplier, (self.channel_index + 1) * self.channel_multiplier)
            ),
            dtype=numpy.dtype("float32"),
            axiskeys=source_data.axiskeys.replace("c", "") + "c" # fastfilters puts channel last
        )

        for data_slice in source_data.cut(c=self.channel_index).split(step_shape):
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

class StructureTensorEigenvalues(FastFilter, FeatureExtractor):
    def __init__(
        self,
        *,
        preprocessor: Optional[Preprocessor] = None,
        innerScale: float,
        outerScale: float,
        window_size: float = 0,
        axis_2d: Optional[Axis2D],
        channel_index: int,
    ):
        super().__init__(preprocessor=preprocessor, axis_2d=axis_2d, channel_index=channel_index)
        self.innerScale = innerScale
        self.outerScale = outerScale
        self.window_size = window_size

    def to_dto(self) -> StructureTensorEigenvaluesDto:
        return StructureTensorEigenvaluesDto(
            axis_2d=self.axis_2d,
            channel_index=self.channel_index,
            innerScale=self.innerScale,
            outerScale=self.outerScale,
            preprocessor=self.preprocessor.to_dto(),
            window_size=self.window_size,
        )

    @classmethod
    def from_dto(cls, dto: StructureTensorEigenvaluesDto) -> "StructureTensorEigenvalues":
        return StructureTensorEigenvalues(
            preprocessor=dto.preprocessor and preprocessor_from_dto(dto.preprocessor),
            innerScale=dto.innerScale,
            outerScale=dto.outerScale,
            window_size=dto.window_size,
            axis_2d=dto.axis_2d,
            channel_index=dto.channel_index,
        )

    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        return fastfilters.structureTensorEigenvalues( # pyright: ignore [reportUnknownVariableType, reportUnknownMemberType]
            source_raw, innerScale=self.innerScale, outerScale=self.outerScale, window_size=self.window_size
        )

    @property
    def channel_multiplier(self) -> int:
        return 2 if self.axis_2d else 3


class GaussianGradientMagnitude(FastFilter, FeatureExtractor):
    def __init__(
        self,
        *,
        preprocessor: Preprocessor = OpRetriever(axiskeys_hint="ctzyx"),
        sigma: float,
        window_size: float = 0,
        axis_2d: Optional[Axis2D],
        channel_index: int,
    ):
        self.sigma = sigma
        self.window_size = window_size
        super().__init__(preprocessor=preprocessor, axis_2d=axis_2d, channel_index=channel_index)

    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        return fastfilters.gaussianGradientMagnitude( # pyright: ignore [reportUnknownVariableType, reportUnknownMemberType]
            source_raw, sigma=self.sigma, window_size=self.window_size
        )

    @property
    def channel_multiplier(self) -> int:
        return 1

    @classmethod
    def from_dto(cls, dto: GaussianGradientMagnitudeDto) -> "GaussianGradientMagnitude":
        return GaussianGradientMagnitude(
            axis_2d=dto.axis_2d,
            channel_index=dto.channel_index,
            preprocessor=preprocessor_from_dto(dto.preprocessor),
            sigma=dto.sigma,
            window_size=dto.window_size,
        )

    def to_dto(self) -> GaussianGradientMagnitudeDto:
        return GaussianGradientMagnitudeDto(
            axis_2d=self.axis_2d,
            channel_index=self.channel_index,
            preprocessor=self.preprocessor.to_dto(),
            sigma=self.sigma,
            window_size=self.window_size
        )

class GaussianSmoothing(FastFilter, FeatureExtractor):
    def __init__(
        self,
        *,
        preprocessor: Preprocessor = OpRetriever(axiskeys_hint="ctzyx"),
        sigma: float,
        window_size: float = 0,
        axis_2d: Optional[Axis2D],
        channel_index: int,
    ):
        self.sigma = sigma
        self.window_size = window_size
        super().__init__(preprocessor=preprocessor, axis_2d=axis_2d, channel_index=channel_index)

    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        return fastfilters.gaussianSmoothing( # pyright: ignore [reportUnknownVariableType, reportUnknownMemberType]
            source_raw, sigma=self.sigma, window_size=self.window_size
        )

    @property
    def channel_multiplier(self) -> int:
        return 1

    @classmethod
    def from_dto(cls, dto: GaussianSmoothingDto) -> "GaussianSmoothing":
        return GaussianSmoothing(
            axis_2d=dto.axis_2d,
            channel_index=dto.channel_index,
            preprocessor=dto.preprocessor.to_dto(),
            sigma=dto.sigma,
            window_size=dto.window_size
        )

    def to_dto(self) -> GaussianSmoothingDto:
        return GaussianSmoothingDto(
            axis_2d=self.axis_2d,
            channel_index=self.channel_index,
            preprocessor=self.preprocessor.to_dto(),
            sigma=self.sigma,
            window_size=self.window_size
        )


class DifferenceOfGaussians(FastFilter, FeatureExtractor):
    def __init__(
        self,
        *,
        preprocessor: Preprocessor = OpRetriever(axiskeys_hint="ctzyx"),
        sigma0: float,
        sigma1: float,
        window_size: float = 0,
        axis_2d: Optional[Axis2D],
        channel_index: int,
    ):
        super().__init__(preprocessor=preprocessor, axis_2d=axis_2d, channel_index=channel_index)
        self.sigma0 = sigma0
        self.sigma1 = sigma1
        self.window_size = window_size

    @property
    def channel_multiplier(self) -> int:
        return 1

    def __repr__(self):
        return f"<{self.__class__.__name__} sigma0:{self.sigma0} sigma1:{self.sigma1} window_size:{self.window_size} axis_2d:{self.axis_2d}>"

    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        a = fastfilters.gaussianSmoothing( # pyright: ignore [reportUnknownVariableType, reportUnknownMemberType]
            source_raw, sigma=self.sigma0, window_size=self.window_size
        )
        b = fastfilters.gaussianSmoothing( # pyright: ignore [reportUnknownVariableType, reportUnknownMemberType]
            source_raw, sigma=self.sigma1, window_size=self.window_size
        )
        return a - b # pyright: ignore [reportUnknownVariableType]

    @classmethod
    def from_dto(cls, dto: DifferenceOfGaussiansDto) -> "DifferenceOfGaussians":
        return DifferenceOfGaussians(
            preprocessor=preprocessor_from_dto(dto.preprocessor),
            axis_2d=dto.axis_2d,
            channel_index=dto.channel_index,
            sigma0=dto.sigma0,
            sigma1=dto.sigma1,
            window_size=dto.window_size,
        )

    def to_dto(self) -> DifferenceOfGaussiansDto:
        return DifferenceOfGaussiansDto(
            preprocessor=self.preprocessor.to_dto(),
            axis_2d=self.axis_2d,
            channel_index=self.channel_index,
            sigma0=self.sigma0,
            sigma1=self.sigma1,
            window_size=self.window_size,
        )


class HessianOfGaussianEigenvalues(FastFilter, FeatureExtractor):
    def __init__(
        self,
        *,
        preprocessor: Preprocessor = OpRetriever(axiskeys_hint="ctzyx"),
        scale: float,
        window_size: float = 0,
        axis_2d: Optional[Axis2D],
        channel_index: int,
    ):
        self.scale = scale
        self.window_size = window_size
        super().__init__(preprocessor=preprocessor, axis_2d=axis_2d, channel_index=channel_index)

    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        return fastfilters.hessianOfGaussianEigenvalues(# pyright: ignore [reportUnknownVariableType, reportUnknownMemberType]
            source_raw, scale=self.scale, window_size=self.window_size
        )

    @property
    def channel_multiplier(self) -> int:
        return 2 if self.axis_2d else 3

    @classmethod
    def from_dto(cls, dto: HessianOfGaussianEigenvaluesDto) -> "HessianOfGaussianEigenvalues":
        return HessianOfGaussianEigenvalues(
            axis_2d=dto.axis_2d,
            channel_index=dto.channel_index,
            preprocessor=preprocessor_from_dto(dto.preprocessor),
            scale=dto.scale,
            window_size=dto.window_size,
        )

    def to_dto(self) -> "HessianOfGaussianEigenvaluesDto":
        return HessianOfGaussianEigenvaluesDto(
            axis_2d=self.axis_2d,
            channel_index=self.channel_index,
            preprocessor=self.preprocessor.to_dto(),
            scale=self.scale,
            window_size=self.window_size,
        )


class LaplacianOfGaussian(FastFilter, FeatureExtractor):
    def __init__(
        self,
        *,
        preprocessor: Preprocessor = OpRetriever(axiskeys_hint="ctzyx"),
        scale: float,
        window_size: float = 0,
        axis_2d: Optional[Axis2D],
        channel_index: int,
    ):
        self.scale = scale
        self.window_size = window_size
        super().__init__(preprocessor=preprocessor, axis_2d=axis_2d, channel_index=channel_index)

    def filter_fn(self, source_raw: "ndarray[Any, dtype[float32]]") -> "ndarray[Any, dtype[float32]]":
        return fastfilters.laplacianOfGaussian(# pyright: ignore [reportUnknownVariableType, reportUnknownMemberType]
            source_raw, scale=self.scale, window_size=self.window_size
        )

    @property
    def channel_multiplier(self) -> int:
        return 1

    @classmethod
    def from_dto(cls, dto: LaplacianOfGaussianDto) -> "LaplacianOfGaussian":
        return LaplacianOfGaussian(
            axis_2d=dto.axis_2d,
            channel_index=dto.channel_index,
            preprocessor=preprocessor_from_dto(dto.preprocessor),
            scale=dto.scale,
            window_size=dto.window_size,
        )

    def to_dto(self) -> "LaplacianOfGaussianDto":
        return LaplacianOfGaussianDto(
            axis_2d=self.axis_2d,
            channel_index=self.channel_index,
            preprocessor=self.preprocessor.to_dto(),
            scale=self.scale,
            window_size=self.window_size,
        )
