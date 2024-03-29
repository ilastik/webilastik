from abc import abstractmethod
from typing import Any, Dict, Iterable, Protocol
from concurrent.futures import Future

import numpy as np
from ndstructs.point5D import Point5D
from ndstructs.array5D import Array5D

from webilastik.serialization.json_serialization import IJsonable
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
        feature_promises: Dict[int, Future[FeatureData]] = {}

        executor = get_executor(hint="feature_extraction", max_workers=len(self.extractors))
        from webilastik.features.ilp_filter import IlpGaussianSmoothing

        feature_promises = {
            fx_index: executor.submit(fx, roi)
            for fx_index, fx in enumerate(self.extractors)
            if isinstance(fx, IlpGaussianSmoothing)
        }
        feature_promises.update({
            fx_index: executor.submit(fx, roi)
            for fx_index, fx in enumerate(self.extractors)
            if not isinstance(fx, IlpGaussianSmoothing)
        })
        assert len(feature_promises) == len(self.extractors)
        features = [feature_promises[i].result() for i in range(len(self.extractors))]

        out = Array5D.allocate(
            dtype=np.dtype("float32"),
            interval=roi.shape.updated(c=sum(feat.shape.c for feat in features)),
            axiskeys="tzyxc",
        ).translated(roi.start)

        channel_offset: int = 0
        for feature in features:
            out.set(feature.translated(Point5D.zero(c=channel_offset)))
            channel_offset += feature.shape.c

        return FeatureData(
            arr=out.raw(out.axiskeys),
            axiskeys=out.axiskeys,
            location=out.location
        )

class JsonableFeatureExtractor(IJsonable, FeatureExtractor, Protocol):
    pass