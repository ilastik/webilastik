from abc import abstractmethod, ABC
from typing import Tuple, Type, TypeVar, List, TypeVar, ClassVar, Mapping, Iterator, Sequence, Dict, Any, Optional
import re


from ndstructs.array5D import Array5D
from ndstructs.utils.json_serializable import JsonValue
import numpy as np

from webilastik.datasource import DataRoi
from .feature_extractor import FeatureExtractor
from webilastik.operator import Operator, OpRetriever


FE = TypeVar("FE", bound="IlpFilter")


class IlpFilter(FeatureExtractor):
    def __init__(self, axis_2d: Optional[str]):
        self.axis_2d = axis_2d
        super().__init__()

    @property
    def channel_multiplier(self) -> int:
        return 1

    @property
    @abstractmethod
    def ilp_scale(self) -> float:
        pass

    @classmethod
    @property
    @abstractmethod
    def ilp_classifier_feature_name(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def from_ilp_scale(
        cls: Type[FE], *, preprocessor: Operator[DataRoi, Array5D] = OpRetriever(), scale: float, axis_2d: Optional[str] = None
    ) -> FE:
        pass

    def to_ilp_classifier_feature_entry(self, channel_index: int) -> str:
        name = f"{self.ilp_classifier_feature_name} (σ={self.ilp_scale})"
        name += " in 2D" if self.axis_2d is not None else " in 3D"
        name += f" [{channel_index}]"
        return name

    @classmethod
    def from_ilp_classifier_feature_entries(cls, entries: Sequence[str]) -> "Sequence[IlpFilter] | ValueError":
        from webilastik.features.channelwise_fastfilters import (
            StructureTensorEigenvalues,
            GaussianGradientMagnitude,
            GaussianSmoothing,
            DifferenceOfGaussians,
            HessianOfGaussianEigenvalues,
            LaplacianOfGaussian,
        )
        filter_classes = {
            StructureTensorEigenvalues.ilp_classifier_feature_name: StructureTensorEigenvalues,
            GaussianGradientMagnitude.ilp_classifier_feature_name: GaussianGradientMagnitude,
            GaussianSmoothing.ilp_classifier_feature_name: GaussianSmoothing,
            DifferenceOfGaussians.ilp_classifier_feature_name: DifferenceOfGaussians,
            HessianOfGaussianEigenvalues.ilp_classifier_feature_name: HessianOfGaussianEigenvalues,
            LaplacianOfGaussian.ilp_classifier_feature_name: LaplacianOfGaussian,
        }

        out: List[IlpFilter] = []
        for entry in entries:
            parts = entry.split()
            # channel_index = int(parts[-1][1:-1]) # strip square brackets off of something like '[3]'
            in_2D = parts[-2] == "2D"
            ilp_scale = float(parts[-4][3:-1]) # read number from something like '(σ=0.3)'
            ilp_classifier_feature_name = "".join(parts[:-4]) # drops the 4 last items, that look like '(σ=0.3) in 2D [0]'


            filter_class = filter_classes.get(ilp_classifier_feature_name)
            if filter_class is None:
                return ValueError(f"Bad ilp filter name: {ilp_classifier_feature_name}")
            ilp_filter = filter_class.from_ilp_scale(
                scale=ilp_scale, axis_2d= "z" if in_2D else None # FIXME: is axis_2d always 'z'?
            )
            if len(out) == 0 or out[-1] != ilp_filter:
                out.append(ilp_filter)
        return out

    @abstractmethod
    def to_json_data(self) -> JsonValue:
        pass