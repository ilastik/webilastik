# pyright: strict

from abc import abstractmethod
import re
from typing import Dict, Final, Optional, Literal, Iterable, List, Sequence, Set, Type

from ndstructs.array5D import Array5D



from webilastik.datasource import DataRoi, DataSource
from webilastik.features.channelwise_fastfilters import (
    Axis2D, FastFilter, DifferenceOfGaussians, GaussianGradientMagnitude, GaussianSmoothing, HessianOfGaussianEigenvalues,
    LaplacianOfGaussian, PresmoothedFilter, StructureTensorEigenvalues
)
from webilastik.serialization import decode_as_utf8
from webilastik.server.rpc.dto import (
    IlpDifferenceOfGaussiansDto,
    IlpFilterCollectionDto,
    IlpFilterDto,
    IlpGaussianGradientMagnitudeDto,
    IlpGaussianSmoothingDto,
    IlpHessianOfGaussianEigenvaluesDto,
    IlpLaplacianOfGaussianDto,
    IlpStructureTensorEigenvaluesDto,
)
from webilastik.utility import parse_float


IlpFilterName = Literal[
    "Gaussian Smoothing",
    "Laplacian of Gaussian",
    "Gaussian Gradient Magnitude",
    "Difference of Gaussians",
    "Structure Tensor Eigenvalues",
    "Hessian of Gaussian Eigenvalues"
]

ilp_classifier_entry_regex: Final[re.Pattern[str]] = re.compile((
    r"(?P<ilp_name>[^\(]+)" +
    r"\(σ=(?P<ilp_scale>[0-9.]+)\) " +
    r"in (?P<filter_dimension>2|3)D" +
    r"( \[(?P<channel_index>\d+)\])?"
))

class IlpFilter(PresmoothedFilter):
    children: Dict[IlpFilterName, Type["IlpFilter"]] = {}

    def is_applicable_to(self, datasource: DataSource) -> bool:
        return self.op.is_applicable_to(datasource)

    @property
    def channel_multiplier(self) -> int:
        return self.op.channel_multiplier

    @property
    @abstractmethod
    def op(self) -> FastFilter:
        pass

    @abstractmethod
    @classmethod
    def ilp_sorting_index(cls) -> Literal[0, 1, 2, 3, 4, 5]:
        pass

    @abstractmethod
    @classmethod
    def ilp_name(cls) -> IlpFilterName:
        pass

    def ilp_classifier_entry(self) -> bytes:
        return f"{self.ilp_name} (σ={self.ilp_scale}) in {2 if self.axis_2d else 3}D [{self.op.channel_index}]".encode("utf8")

    def __call__(self, /, roi: DataRoi) -> Array5D:
        return self.op(roi)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, IlpFilter):
            return (self.ilp_sorting_index, self.ilp_scale, self.op.channel_index) < (other.ilp_sorting_index, other.ilp_scale, other.op.channel_index)
        return True # FIXME: ?

    @classmethod
    def ilp_sorted(cls, filters: Iterable["IlpFilter"]) -> List["IlpFilter"]:
        return sorted(filters)

    @abstractmethod
    def to_dto(self) -> IlpFilterDto:
        pass

    def __eq__(self, other: object):
        #FIXME: maybe doing this statically would be safer
        return isinstance(other, IlpFilter) and self.__class__ == other.__class__ and self.ilp_scale == other.ilp_scale

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        IlpFilter.children[cls.ilp_name()] = cls

    @staticmethod
    def ilp_filter_from_dto(dto: IlpFilterDto) -> "IlpFilter":
        if isinstance(dto, IlpStructureTensorEigenvaluesDto):
            return IlpStructureTensorEigenvalues.from_dto(dto)
        if isinstance(dto, IlpGaussianGradientMagnitudeDto):
            return IlpGaussianGradientMagnitude.from_dto(dto)
        if isinstance(dto, IlpGaussianSmoothingDto):
            return IlpGaussianSmoothing.from_dto(dto)
        if isinstance(dto, IlpDifferenceOfGaussiansDto):
            return IlpDifferenceOfGaussians.from_dto(dto)
        if isinstance(dto, IlpHessianOfGaussianEigenvaluesDto):
            return IlpHessianOfGaussianEigenvalues.from_dto(dto)
        return IlpLaplacianOfGaussian.from_dto(dto)

    @staticmethod
    def ilp_filter_from_ilp_classifier_entry(entry: bytes) -> "IlpFilter | Exception":
        str_result = decode_as_utf8(entry)
        if isinstance(str_result, Exception):
            return str_result

        match = ilp_classifier_entry_regex.fullmatch(str_result)
        if not match:
            return Exception(f"Bad ilp classifier feature entry: {str_result}")

        ilp_scale_str = match.group("ilp_scale")
        ilp_scale_result = parse_float(ilp_scale_str)
        if isinstance(ilp_scale_result, Exception):
            return Exception(f"Bad ilp scale: {ilp_scale_str}")

        is_2D = match.group("filter_dimension") == "2"
        channel_index = int(match.group("channel_index").strip("[]"))
        ilp_name: str = match.group("ilp_name")
        ilp_name = ilp_name.strip()

        ilp_klass = IlpFilter.children.get(ilp_name)

        if IlpStructureTensorEigenvaluesDto.ilp_name == ilp_name:
            return IlpStructureTensorEigenvalues(ilp_scale=ilp_scale_result, axis_2d="z" if is_2D else None, channel_index=channel_index)
        if IlpGaussianGradientMagnitudeDto.ilp_name == ilp_name:
            return IlpGaussianGradientMagnitude(ilp_scale=ilp_scale_result, axis_2d="z" if is_2D else None, channel_index=channel_index)
        if IlpGaussianSmoothingDto.ilp_name == ilp_name:
            return IlpGaussianSmoothing(ilp_scale=ilp_scale_result, axis_2d="z" if is_2D else None, channel_index=channel_index)
        if IlpDifferenceOfGaussiansDto.ilp_name == ilp_name:
            return IlpDifferenceOfGaussians(ilp_scale=ilp_scale_result, axis_2d="z" if is_2D else None, channel_index=channel_index)
        if IlpHessianOfGaussianEigenvaluesDto.ilp_name == ilp_name:
            return IlpHessianOfGaussianEigenvalues(ilp_scale=ilp_scale_result, axis_2d="z" if is_2D else None, channel_index=channel_index)
        return IlpLaplacianOfGaussian.from_dto(dto)


class IlpFilterCollection:
    DEFAULT_SCALES: Sequence[float] = [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0]
    def __init__(self, filters: Set[IlpFilter]) -> None:
        self.filters: Final[Sequence[IlpFilter]] = IlpFilter.ilp_sorted(filters)
        super().__init__()

    def to_dto(self) -> IlpFilterCollectionDto:
        return IlpFilterCollectionDto(
            filters=tuple(f.to_dto() for f in self.filters)
        )

    @classmethod
    def from_dto(cls, dto: IlpFilterCollectionDto) -> "IlpFilterCollection":
        return IlpFilterCollection(set(ilp_filter_from_dto(f) for f in dto.filters))

    @classmethod
    def none(cls) -> "IlpFilterCollection":
        return IlpFilterCollection(set())

    @classmethod
    def all(cls, num_channels: int) -> "IlpFilterCollection":
        feature_extractors_classes = [
            IlpGaussianSmoothing,
            IlpLaplacianOfGaussian,
            IlpGaussianGradientMagnitude,
            IlpDifferenceOfGaussians,
            IlpStructureTensorEigenvalues,
            IlpHessianOfGaussianEigenvalues,
        ]
        return IlpFilterCollection(set(
            [IlpGaussianSmoothing(ilp_scale=0.3, axis_2d="z", channel_index=channel_index) for channel_index in range(num_channels)] +
            [
                extractor_class(ilp_scale=scale, axis_2d="z", channel_index=channel_index)
                for extractor_class in feature_extractors_classes
                for scale in (cls.DEFAULT_SCALES[1:])
                for channel_index in range(num_channels)
            ]
        ))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IlpFilterCollection):
            return False
        return all(f1 == f2 for f1, f2 in zip(self.filters, other.filters))


class IlpGaussianSmoothing(IlpFilter):
    def __init__(
        self,
        ilp_scale: float,
        axis_2d: Optional[Axis2D],
        channel_index: int,
    ):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d,  channel_index=channel_index)
        self._op = GaussianSmoothing(
            preprocessor=self.presmoother,
            sigma=min(ilp_scale, 1.0),
            axis_2d=axis_2d,
            channel_index=channel_index,
        )

    def to_dto(self) -> IlpGaussianSmoothingDto:
        return IlpGaussianSmoothingDto(
            ilp_scale=self.ilp_scale,
            axis_2d=self.axis_2d,
            channel_index=self.op.channel_index,
        )

    @classmethod
    def from_dto(cls, dto: IlpGaussianSmoothingDto) -> "IlpGaussianSmoothing":
        return IlpGaussianSmoothing(
            ilp_scale=dto.ilp_scale,
            axis_2d=dto.axis_2d,
            channel_index=dto.channel_index,
        )

    @property
    def op(self) -> GaussianSmoothing:
        return self._op

    @classmethod
    def ilp_sorting_index(cls) -> Literal[0]:
        return 0

    @classmethod
    def ilp_name(cls) -> IlpFilterName:
        return "Gaussian Smoothing"


class IlpLaplacianOfGaussian(IlpFilter):
    def __init__(
        self,
        *,
        ilp_scale: float,
        axis_2d: Optional[Axis2D],
        channel_index: int,
    ):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, channel_index=channel_index)
        self._op = LaplacianOfGaussian(
            preprocessor=self.presmoother,
            scale=min(ilp_scale, 1.0),
            axis_2d=axis_2d,
            channel_index=channel_index
        )

    def to_dto(self) -> IlpLaplacianOfGaussianDto:
        return IlpLaplacianOfGaussianDto(
            ilp_scale=self.ilp_scale,
            axis_2d=self.axis_2d,
            channel_index=self.op.channel_index,
        )

    @classmethod
    def from_dto(cls, dto: IlpLaplacianOfGaussianDto) -> "IlpLaplacianOfGaussian":
        return IlpLaplacianOfGaussian(
            ilp_scale=dto.ilp_scale,
            axis_2d=dto.axis_2d,
            channel_index=dto.channel_index,
        )

    @property
    def op(self) -> LaplacianOfGaussian:
        return self._op

    @classmethod
    def ilp_sorting_index(cls) -> Literal[1]:
        return 1

    @classmethod
    def ilp_name(cls) -> IlpFilterName:
        return "Laplacian of Gaussian"

class IlpGaussianGradientMagnitude(IlpFilter):
    def __init__(
        self,
        *,
        ilp_scale: float,
        axis_2d: Optional[Axis2D],
        channel_index: int,
    ):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, channel_index=channel_index)
        self._op = GaussianGradientMagnitude(
            preprocessor=self.presmoother,
            sigma=min(ilp_scale, 1.0),
            axis_2d=axis_2d,
            channel_index=channel_index,
        )

    def to_dto(self) -> IlpGaussianGradientMagnitudeDto:
        return IlpGaussianGradientMagnitudeDto(
            ilp_scale=self.ilp_scale,
            axis_2d=self.axis_2d,
            channel_index=self.op.channel_index,
        )

    @classmethod
    def from_dto(cls, dto: IlpGaussianGradientMagnitudeDto) -> "IlpGaussianGradientMagnitude":
        return IlpGaussianGradientMagnitude(
            ilp_scale=dto.ilp_scale,
            axis_2d=dto.axis_2d,
            channel_index=dto.channel_index,
        )

    @property
    def op(self) -> GaussianGradientMagnitude:
        return self._op

    @classmethod
    def ilp_sorting_index(cls) -> Literal[2]:
        return 2

    @classmethod
    def ilp_name(cls) -> IlpFilterName:
        return "Gaussian Gradient Magnitude"

class IlpDifferenceOfGaussians(IlpFilter):
    def __init__(
        self,
        ilp_scale: float,
        axis_2d: Optional[Axis2D],
        channel_index: int,
    ):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, channel_index=channel_index)
        capped_scale = min(ilp_scale, 1.0)
        self._op = DifferenceOfGaussians(
            preprocessor=self.presmoother,
            sigma0=capped_scale,
            sigma1=capped_scale * 0.66,
            axis_2d=axis_2d,
            channel_index=channel_index,
        )

    def to_dto(self) -> IlpDifferenceOfGaussiansDto:
        return IlpDifferenceOfGaussiansDto(
            ilp_scale=self.ilp_scale,
            axis_2d=self.axis_2d,
            channel_index=self.op.channel_index,
        )

    @classmethod
    def from_dto(cls, dto: IlpDifferenceOfGaussiansDto) -> "IlpDifferenceOfGaussians":
        return IlpDifferenceOfGaussians(
            ilp_scale=dto.ilp_scale,
            axis_2d=dto.axis_2d,
            channel_index=dto.channel_index,
        )

    @property
    def op(self) -> DifferenceOfGaussians:
        return self._op

    @classmethod
    def ilp_sorting_index(cls) -> Literal[3]:
        return 3

    @classmethod
    def ilp_name(cls) -> IlpFilterName:
        return "Difference of Gaussians"

class IlpStructureTensorEigenvalues(IlpFilter):
    def __init__(
        self,
        *,
        ilp_scale: float,
        axis_2d: Optional[Axis2D],
        channel_index: int,
    ):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, channel_index=channel_index)
        capped_scale = min(ilp_scale, 1.0)
        self._op = StructureTensorEigenvalues(
            innerScale=capped_scale,
            outerScale=0.5 * capped_scale,
            axis_2d=axis_2d,
            preprocessor=self.presmoother,
            channel_index=channel_index,
        )

    def to_dto(self) -> IlpStructureTensorEigenvaluesDto:
        return IlpStructureTensorEigenvaluesDto(
            ilp_scale=self.ilp_scale,
            axis_2d=self.axis_2d,
            channel_index=self.op.channel_index,
        )

    @classmethod
    def from_dto(cls, dto: IlpStructureTensorEigenvaluesDto) -> "IlpStructureTensorEigenvalues":
        return IlpStructureTensorEigenvalues(
            ilp_scale=dto.ilp_scale,
            axis_2d=dto.axis_2d,
            channel_index=dto.channel_index,
        )

    @property
    def op(self) -> StructureTensorEigenvalues:
        return self._op

    @classmethod
    def ilp_sorting_index(cls) -> Literal[4]:
        return 4

    @classmethod
    def ilp_name(cls) -> IlpFilterName:
        return "Structure Tensor Eigenvalues"

class IlpHessianOfGaussianEigenvalues(IlpFilter):
    def __init__(self, *, ilp_scale: float, channel_index: int, axis_2d: Optional[Axis2D],):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, channel_index=channel_index)
        self._op = HessianOfGaussianEigenvalues(
            preprocessor=self.presmoother,
            scale=min(ilp_scale, 1.0),
            channel_index=channel_index,
            axis_2d=axis_2d,
        )

    def to_dto(self) -> IlpHessianOfGaussianEigenvaluesDto:
        return IlpHessianOfGaussianEigenvaluesDto(
            ilp_scale=self.ilp_scale,
            axis_2d=self.axis_2d,
            channel_index=self.op.channel_index,
        )

    @classmethod
    def from_dto(cls, dto: IlpHessianOfGaussianEigenvaluesDto) -> "IlpHessianOfGaussianEigenvalues":
        return IlpHessianOfGaussianEigenvalues(
            ilp_scale=dto.ilp_scale,
            axis_2d=dto.axis_2d,
            channel_index=dto.channel_index,
        )

    @property
    def op(self) -> HessianOfGaussianEigenvalues:
        return self._op

    @classmethod
    def ilp_sorting_index(cls) -> Literal[5]:
        return 5

    @classmethod
    def ilp_name(cls) -> IlpFilterName:
        return "Hessian of Gaussian Eigenvalues"
