from abc import abstractmethod, ABC
import functools
from typing import List, Iterable, Optional, Type, Union, Iterator
from joblib.externals.cloudpickle.cloudpickle import instance
from ndstructs.array5D import All, SPAN_OVERRIDE

import numpy as np

from ndstructs import Interval5D, Point5D, Shape5D, SPAN
from ndstructs import Array5D
from ndstructs.datasource import DataSource, DataRoi

from webilastik.operator import Operator

class FeatureData(Array5D):
    def __init__(self, arr: np.ndarray, axiskeys: str, location: Point5D = Point5D.zero()):
        super().__init__(arr, axiskeys=axiskeys, location=location)
        assert self.dtype == np.dtype('float32')


class FeatureDataMismatchException(Exception):
    def __init__(self, feature_extractor: "FeatureExtractor", data_source: DataSource):
        super().__init__(f"Feature {feature_extractor} can't be cleanly applied to {data_source}")


class FeatureExtractor(Operator[DataRoi, FeatureData]):
    """A specification of how feature data is to be (reproducibly) computed"""

    @abstractmethod
    def is_applicable_to(self, datasource: DataSource) -> bool:
        pass

    def ensure_applicable(self, datasource: DataSource):
        if not self.is_applicable_to(datasource):
            raise FeatureDataMismatchException(self, datasource)

    def __hash__(self):
        return hash((self.__class__, tuple(self.__dict__.values())))

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__


class FeatureExtractorCollection(FeatureExtractor):
    def __init__(self, extractors: Iterable[FeatureExtractor]):
        self.extractors = tuple(extractors)
        assert len(self.extractors) > 0

    def is_applicable_to(self, datasource: DataSource) -> bool:
        return all(fx.is_applicable_to(datasource) for fx in self.extractors)

    def compute(self, roi: DataRoi) -> FeatureData:
        features: List[FeatureData] = []
        channel_offset: int = 0
        for fx in self.extractors:
            result = fx.compute(roi).translated(Point5D.zero(c=channel_offset))
            features.append(result)
            channel_offset += result.shape.c
        out = Array5D.combine(features)
        return FeatureData(
            arr=out.raw(out.axiskeys),
            axiskeys=out.axiskeys,
            location=out.location
        )
