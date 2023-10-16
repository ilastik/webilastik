# pyright: strict

from typing import Protocol, TypeVar
from webilastik.features.feature_extractor import FeatureExtractorCollection

from webilastik.server.rpc.dto import (
    OpRetrieverDto,
    FeatureExtractorCollectionDto,
    GaussianSmoothingDto,
    LaplacianOfGaussianDto,
    GaussianGradientMagnitudeDto,
    DifferenceOfGaussiansDto,
    PreprocessorDto,
    StructureTensorEigenvaluesDto,
    HessianOfGaussianEigenvaluesDto,
)

from webilastik.datasource import DataRoi, DataSource
from ndstructs.array5D import Array5D

IN = TypeVar("IN", contravariant=True)
OUT = TypeVar("OUT", covariant=True)

class Operator(Protocol[IN, OUT]):
    def __call__(self, /, input: IN) -> OUT: ...

class Preprocessor(Operator[DataRoi, Array5D], Protocol):
    def to_dto(self) -> PreprocessorDto: ...
    def is_applicable_to(self, datasource: DataSource) -> bool: ...

def preprocessor_from_dto(dto: PreprocessorDto) -> Preprocessor:
    from webilastik.features.channelwise_fastfilters import (
        StructureTensorEigenvalues,
        GaussianGradientMagnitude,
        GaussianSmoothing,
        DifferenceOfGaussians,
        HessianOfGaussianEigenvalues,
        LaplacianOfGaussian,
    )
    from webilastik.features.ilp_filter import ilp_filter_from_dto

    if isinstance(dto, StructureTensorEigenvaluesDto):
        return StructureTensorEigenvalues.from_dto(dto)
    if isinstance(dto, GaussianGradientMagnitudeDto):
        return GaussianGradientMagnitude.from_dto(dto)
    if isinstance(dto, GaussianSmoothingDto):
        return GaussianSmoothing.from_dto(dto)
    if isinstance(dto, DifferenceOfGaussiansDto):
        return DifferenceOfGaussians.from_dto(dto)
    if isinstance(dto, HessianOfGaussianEigenvaluesDto):
        return HessianOfGaussianEigenvalues.from_dto(dto)
    if isinstance(dto, LaplacianOfGaussianDto):
        return LaplacianOfGaussian.from_dto(dto)

    if isinstance(dto, FeatureExtractorCollectionDto):
        return FeatureExtractorCollection.from_dto(dto)
    # if isinstance(dto, IlpFilterCollectionDto):
    #     return IlpFilterCollection.from_dto(dto)

    if isinstance(dto, OpRetrieverDto):
        return OpRetriever.from_dto(dto)

    return ilp_filter_from_dto(dto)


class OpRetriever(Preprocessor):
    def __init__(self, axiskeys_hint: str = "ctzyx") -> None:
        self.axiskeys_hint = axiskeys_hint
        super().__init__()

    def to_dto(self) -> OpRetrieverDto:
        return OpRetrieverDto(axiskeys_hint=self.axiskeys_hint)

    def is_applicable_to(self, datasource: DataSource) -> bool:
        return True

    @classmethod
    def from_dto(cls, dto: OpRetrieverDto) -> "OpRetriever":
        # FIXME: check axes are good
        return OpRetriever(axiskeys_hint=dto.axiskeys_hint)

    def __call__(self, /, roi: DataRoi) -> Array5D:
        return roi.retrieve(axiskeys_hint=self.axiskeys_hint)

