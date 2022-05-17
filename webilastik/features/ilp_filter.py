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
    @abstractmethod
    def from_ilp_scale(
        cls: Type[FE], *, preprocessor: Operator[DataRoi, Array5D] = OpRetriever(), scale: float, axis_2d: Optional[str] = None
    ) -> FE:
        pass

    @abstractmethod
    def to_json_data(self) -> JsonValue:
        pass