from abc import abstractmethod
from typing import Final, Mapping, Optional, Literal, Iterable, List, Sequence, Set


from ndstructs.array5D import Array5D
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonFloat, ensureJsonObject, ensureJsonString

from webilastik.datasource import DataRoi, DataSource
from webilastik.features.channelwise_fastfilters import (
    Axis2D, ChannelwiseFastFilter, DifferenceOfGaussians, GaussianGradientMagnitude, GaussianSmoothing, HessianOfGaussianEigenvalues,
    LaplacianOfGaussian, PresmoothedFilter, StructureTensorEigenvalues, get_axis_2d
)
from .feature_extractor import FeatureData, JsonableFeatureExtractor
from webilastik.operator import Operator, OpRetriever
from webilastik.server.rpc.dto import IlpFeatureExtractorDto

IlpFilterName = Literal[
    "Gaussian Smoothing",
    "Laplacian of Gaussian",
    "Gaussian Gradient Magnitude",
    "Difference of Gaussians",
    "Structure Tensor Eigenvalues",
    "Hessian of Gaussian Eigenvalues"
]

ILP_FILTER_INDICES: Mapping[IlpFilterName, int] = {
    "Gaussian Smoothing": 0,
    "Laplacian of Gaussian": 1,
    "Gaussian Gradient Magnitude": 2,
    "Difference of Gaussians": 3,
    "Structure Tensor Eigenvalues": 4,
    "Hessian of Gaussian Eigenvalues": 5
}

class IlpFilter(PresmoothedFilter):
    def to_dto(self) -> IlpFeatureExtractorDto:
        return IlpFeatureExtractorDto(
            ilp_scale=self.ilp_scale,
            axis_2d=self.axis_2d,
            class_name=self.ilp_name(),
        )

    def is_applicable_to(self, datasource: DataSource) -> bool:
        return self.op.is_applicable_to(datasource)

    @property
    def channel_multiplier(self) -> int:
        return self.op.channel_multiplier

    @classmethod
    def from_dto(cls, value: IlpFeatureExtractorDto) -> "IlpFilter":
        class_name = value.class_name

        if class_name == IlpGaussianSmoothing.ilp_name():
            return IlpGaussianSmoothing(ilp_scale=value.ilp_scale, axis_2d=value.axis_2d)
        if class_name == IlpLaplacianOfGaussian.ilp_name():
            return IlpLaplacianOfGaussian(ilp_scale=value.ilp_scale, axis_2d=value.axis_2d)
        if class_name == IlpGaussianGradientMagnitude.ilp_name():
            return IlpGaussianGradientMagnitude(ilp_scale=value.ilp_scale, axis_2d=value.axis_2d)
        if class_name == IlpDifferenceOfGaussians.ilp_name():
            return IlpDifferenceOfGaussians(ilp_scale=value.ilp_scale, axis_2d=value.axis_2d)
        if class_name == IlpStructureTensorEigenvalues.ilp_name():
            return IlpStructureTensorEigenvalues(ilp_scale=value.ilp_scale, axis_2d=value.axis_2d)
        if class_name == IlpHessianOfGaussianEigenvalues.ilp_name():
            return IlpHessianOfGaussianEigenvalues(ilp_scale=value.ilp_scale, axis_2d=value.axis_2d)
        raise Exception(f"Bad class_name for IlpFilter: {class_name}")

    @property
    @abstractmethod
    def op(self) -> ChannelwiseFastFilter:
        pass

    @classmethod
    @abstractmethod
    def ilp_name(cls) -> IlpFilterName:
        pass

    @property
    @abstractmethod
    def ilp_sorting_index(self) -> int:
        pass

    def __call__(self, /, roi: DataRoi) -> FeatureData:
        return self.op(roi)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, IlpFilter):
            return (self.ilp_sorting_index, self.ilp_scale) < (other.ilp_sorting_index, other.ilp_scale)
        return True # FIXME: ?

    @classmethod
    def ilp_sorted(cls, filters: Iterable["IlpFilter"]) -> List["IlpFilter"]:
        return sorted(filters)

class IlpFilterCollection:
    DEFAULT_SCALES: Sequence[float] = [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0]
    def __init__(self, filters: Set[IlpFilter]) -> None:
        self.filters: Final[Sequence[IlpFilter]] = IlpFilter.ilp_sorted(filters)
        super().__init__()

    @classmethod
    def none(cls) -> "IlpFilterCollection":
        return IlpFilterCollection(set())

    @classmethod
    def all(cls) -> "IlpFilterCollection":
        feature_extractors_classes = [
            IlpGaussianSmoothing,
            IlpLaplacianOfGaussian,
            IlpGaussianGradientMagnitude,
            IlpDifferenceOfGaussians,
            IlpStructureTensorEigenvalues,
            IlpHessianOfGaussianEigenvalues,
        ]
        return IlpFilterCollection(set(
            [IlpGaussianSmoothing(ilp_scale=0.3, axis_2d="z")] +
            [
                extractor_class(ilp_scale=scale, axis_2d="z")
                for extractor_class in feature_extractors_classes
                for scale in (cls.DEFAULT_SCALES[1:])
            ]
        ))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IlpFilterCollection):
            return False
        return all(f1 == f2 for f1, f2 in zip(self.filters, other.filters))


class IlpGaussianSmoothing(IlpFilter):
    def __init__(
        self, ilp_scale: float, axis_2d: Optional[Axis2D], preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx")
    ):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, preprocessor=preprocessor)
        self._op = GaussianSmoothing(
            preprocessor=self.presmoother,
            sigma=min(ilp_scale, 1.0),
            axis_2d=axis_2d,
        )

    @classmethod
    def ilp_name(cls) -> Literal["Gaussian Smoothing"]:
        return "Gaussian Smoothing"

    @property
    def op(self) -> GaussianSmoothing:
        return self._op

    @property
    def ilp_sorting_index(self) -> int:
        return 0

class IlpLaplacianOfGaussian(IlpFilter):
    def __init__(
        self, ilp_scale: float, axis_2d: Optional[Axis2D], preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx")
    ):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, preprocessor=preprocessor)
        self._op = LaplacianOfGaussian(
            preprocessor=self.presmoother,
            scale=min(ilp_scale, 1.0),
            axis_2d=axis_2d,
        )

    @classmethod
    def ilp_name(cls) -> Literal["Laplacian of Gaussian"]:
        return "Laplacian of Gaussian"

    @property
    def op(self) -> LaplacianOfGaussian:
        return self._op

    @property
    def ilp_sorting_index(self) -> int:
        return 1

class IlpGaussianGradientMagnitude(IlpFilter):
    def __init__(
        self, ilp_scale: float, axis_2d: Optional[Axis2D], preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx")
    ):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, preprocessor=preprocessor)
        self._op = GaussianGradientMagnitude(
            preprocessor=self.presmoother,
            sigma=min(ilp_scale, 1.0),
            axis_2d=axis_2d,
        )

    @classmethod
    def ilp_name(cls) -> Literal["Gaussian Gradient Magnitude"]:
        return "Gaussian Gradient Magnitude"

    @property
    def op(self) -> GaussianGradientMagnitude:
        return self._op

    @property
    def ilp_sorting_index(self) -> int:
        return 2

class IlpDifferenceOfGaussians(IlpFilter):
    def __init__(
        self, ilp_scale: float, axis_2d: Optional[Axis2D], preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx")
    ):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, preprocessor=preprocessor)
        capped_scale = min(ilp_scale, 1.0)
        self._op = DifferenceOfGaussians(
            preprocessor=self.presmoother,
            sigma0=capped_scale,
            sigma1=capped_scale * 0.66,
            axis_2d=axis_2d,
        )

    @classmethod
    def ilp_name(cls) -> Literal["Difference of Gaussians"]:
        return "Difference of Gaussians"

    @property
    def op(self) -> DifferenceOfGaussians:
        return self._op

    @property
    def ilp_sorting_index(self) -> int:
        return 3

class IlpStructureTensorEigenvalues(IlpFilter):
    def __init__(
        self, *, ilp_scale: float, axis_2d: Optional[Axis2D], preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx")
    ):
        super().__init__(ilp_scale=ilp_scale, preprocessor=preprocessor, axis_2d=axis_2d)
        capped_scale = min(ilp_scale, 1.0)
        self._op = StructureTensorEigenvalues(
            innerScale=capped_scale,
            outerScale=0.5 * capped_scale,
            axis_2d=axis_2d,
            preprocessor=self.presmoother,
        )

    @classmethod
    def ilp_name(cls) -> Literal["Structure Tensor Eigenvalues"]:
        return "Structure Tensor Eigenvalues"

    @property
    def op(self) -> StructureTensorEigenvalues:
        return self._op

    @property
    def ilp_sorting_index(self) -> int:
        return 4

class IlpHessianOfGaussianEigenvalues(IlpFilter):
    def __init__(self, ilp_scale: float, axis_2d: Optional[Axis2D]):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d)
        self._op = HessianOfGaussianEigenvalues(
            preprocessor=self.presmoother,
            scale=min(ilp_scale, 1.0),
            axis_2d=axis_2d,
        )

    @classmethod
    def ilp_name(cls) -> Literal["Hessian of Gaussian Eigenvalues"]:
        return "Hessian of Gaussian Eigenvalues"

    @property
    def op(self) -> HessianOfGaussianEigenvalues:
        return self._op

    @property
    def ilp_sorting_index(self) -> int:
        return 5