from abc import abstractmethod, ABC
from typing import Any, List, Iterable, Protocol
import time
from concurrent.futures import as_completed

import numpy as np
from ndstructs.point5D import Point5D
from ndstructs.array5D import Array5D
from ndstructs.utils.json_serializable import IJsonable

from webilastik.datasource import DataSource, DataRoi
from webilastik.operator import Operator
from executor_getter import get_executor

class FeatureData(Array5D):
    def __init__(self, arr: "np.ndarray[Any, np.dtype[np.float32]]", axiskeys: str, location: Point5D = Point5D.zero()):
        super().__init__(arr, axiskeys=axiskeys, location=location)
        assert self.dtype == np.dtype('float32')


class FeatureDataMismatchException(Exception):
    def __init__(self, feature_extractor: "FeatureExtractor", data_source: DataSource):
        super().__init__(f"Feature {feature_extractor} can't be cleanly applied to {data_source}")


class FeatureExtractor(Operator[DataRoi, FeatureData], Protocol):
    """A specification of how feature data is to be (reproducibly) computed"""

    @abstractmethod
    def __call__(self, /, roi: DataRoi) -> FeatureData:
        pass

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
        super().__init__()

    def is_applicable_to(self, datasource: DataSource) -> bool:
        return all(fx.is_applicable_to(datasource) for fx in self.extractors)

    def __call__(self, /, roi: DataRoi) -> FeatureData:
        assert roi.interval.c[0] == 0
        features: List[FeatureData] = []

        channel_offset: int = 0
        t0 = time.time()
        executor = get_executor(hint="feature_extraction", max_workers=len(self.extractors))
        for fut in [executor.submit(fx, roi) for fx in self.extractors]:
            result = fut.result().translated(Point5D.zero(c=channel_offset))
            features.append(result)
            channel_offset += result.shape.c
        t1 = time.time()
        print(f"computed features in {t1 - t0}s")

        out = Array5D.allocate(
            dtype=np.dtype("float32"),
            interval=roi.shape.updated(c=sum(feat.shape.c for feat in features)),
            axiskeys="ctzyx",
        ).translated(roi.start)
        print(f"Allocated {out} for storing features of {roi.interval}")

        t0 = time.time()
        for feature in features:
            out.set(feature)
        t1 = time.time()
        print(f"Copied features in {t1 - t0}s")

        return FeatureData(
            arr=out.raw(out.axiskeys),
            axiskeys=out.axiskeys,
            location=out.location
        )

class JsonableFeatureExtractor(IJsonable, FeatureExtractor, Protocol):
    pass