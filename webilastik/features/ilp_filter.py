from abc import abstractmethod, ABC
from typing import Type, TypeVar, List, TypeVar, ClassVar, Mapping, Iterator, Sequence, Dict, Any, Optional
import re

import numpy as np
from ndstructs.utils import from_json_data, Dereferencer


from .feature_extractor import ChannelwiseFilter
from webilastik.operator import Operator, NoopOperator


FE = TypeVar("FE", bound="IlpFilter")


class IlpFilter(ChannelwiseFilter):
    REGISTRY: ClassVar[Dict[str, Type[FE]]] = {}

    def get_expected_dtype(self, input_dtype: np.dtype) -> np.dtype:
        return np.dtype("float32")

    @property
    @abstractmethod
    def ilp_scale(self) -> float:
        pass

    @classmethod
    @abstractmethod
    def from_ilp_scale(
        cls: Type[FE], *, preprocessor: Operator = NoopOperator(), scale: float, axis_2d: Optional[str] = None
    ) -> FE:
        pass

    @property
    def ilp_name(self) -> str:
        name = re.sub(r"([a-z])([A-Z])", r"\1___\2", self.__class__.__name__).replace("___", " ").title()
        name = re.sub(r"\bOf\b", "of", name)
        name += f" (σ={self.ilp_scale})"
        name += " in 2D" if self.axis_2d is not None else " in 3D"
        return name

    # @classmethod
    # def from_ilp_classifier_feature_name(cls, feature_name: bytes) -> "ChannelwiseFilter":
    #     description = feature_name.decode("utf8")
    #     name = re.search(r"^(?P<name>[a-zA-Z \-]+)", description).group("name").strip()
    #     klass = cls.REGISTRY[name.title().replace(" ", "")]
    #     scale = float(re.search(r"σ=(?P<sigma>[0-9.]+)", description).group("sigma"))
    #     return klass.from_ilp_scale(scale=scale, axis_2d="z" if "in 2D" in description else None)

    @classmethod
    def from_ilp_classifier_feature_names(cls, feature_names: List[bytes]) -> List["ChannelwiseFilter"]:
        feature_extractors: List[ChannelwiseFilter] = []
        for feature_description in feature_names:
            extractor = cls.from_ilp_feature_name(feature_description)
            if len(feature_extractors) == 0 or feature_extractors[-1] != extractor:
                feature_extractors.append(extractor)
        return feature_extractors

    @classmethod
    def from_ilp_data(cls, data: Mapping) -> List["IlpFilter"]:
        feature_names: List[str] = [feature_name.decode("utf-8") for feature_name in data["FeatureIds"][()]]
        compute_in_2d: List[bool] = list(data["ComputeIn2d"][()])
        scales: List[float] = list(data["Scales"][()])
        selection_matrix = data["SelectionMatrix"][()]  # feature name x scales

        feature_extractors = []
        for feature_idx, feature_name in enumerate(feature_names):
            feature_class = IlpFilter.REGISTRY[feature_name]
            for scale_idx, (scale, in_2d) in enumerate(zip(scales, compute_in_2d)):
                if selection_matrix[feature_idx][scale_idx]:
                    axis_2d = "z" if in_2d else None
                    extractor = feature_class.from_ilp_scale(
                        scale=scale, axis_2d=axis_2d
                    )
                    feature_extractors.append(extractor)
        return feature_extractors

    @classmethod
    def from_json_data(cls, data, dereferencer: Optional[Dereferencer] = None) -> "IlpFilter":
        return cls.REGISTRY[data["__class__"]].from_json_data(data, dereferencer=dereferencer)

    # def to_ilp_feature_names(self) -> Iterator[bytes]:
    #     for c in range(self.num_input_channels * self.channel_multiplier):
    #         name_and_channel = self.ilp_name + f" [{c}]"
    #         yield name_and_channel.encode("utf8")
