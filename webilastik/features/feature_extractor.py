from abc import abstractmethod, ABC
import functools
from typing import List, Iterable, Optional, Type, Union, Iterator

import numpy as np

from ndstructs import Interval5D, Point5D, Shape5D
from ndstructs import Array5D
from ndstructs.datasource import DataSource, DataRoi
from ndstructs.utils import JsonSerializable

from webilastik.operator import Operator

class FeatureData(Array5D):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # FIXME:
        # assert arr.dtype == np.float32


class FeatureDataMismatchException(Exception):
    def __init__(self, feature_extractor: "FeatureExtractor", data_source: DataSource):
        super().__init__(f"Feature {feature_extractor} can't be cleanly applied to {data_source}")


class FeatureExtractor(Operator, JsonSerializable):
    """A specification of how feature data is to be (reproducibly) computed"""

    def __hash__(self):
        return hash((self.__class__, tuple(self.__dict__.values())))

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    @abstractmethod
    def get_expected_shape(self, input_shape: Shape5D) -> Shape5D:
        pass

    def allocate_for(self, input_shape: Shape5D) -> FeatureData:
        # FIXME: vigra needs C to be the last REAL axis rather than the last axis of the view -.-
        out_roi = self.get_expected_shape(input_shape).to_interval5d()
        return FeatureData.allocate(out_roi, dtype=np.dtype('float32'), axiskeys="tzyxc")

    @functools.lru_cache()
    def compute(self, roi: DataRoi) -> FeatureData:
        out_features = self.allocate_for(roi.shape).translated(roi.start)
        self.compute_into(roi, out_features)
        out_features.setflags(write=False)
        return out_features

    @abstractmethod
    def compute_into(self, roi: DataRoi, out: FeatureData) -> FeatureData:
        pass

    def is_applicable_to(self, datasource: DataSource) -> bool:
        return datasource.shape >= self.kernel_shape

    def ensure_applicable(self, datasource: DataSource):
        if not self.is_applicable_to(datasource):
            raise FeatureDataMismatchException(self, datasource)

    @property
    @abstractmethod
    def kernel_shape(self) -> Shape5D:
        pass

    @property
    def halo(self) -> Point5D:
        return self.kernel_shape // 2


class ChannelwiseFilter(FeatureExtractor):
    """A Feature extractor that computes independently for every
    spatial slice and for every channel in its input"""

    def __init__(self, *, axis_2d: Optional[str] = None):
        super().__init__()
        self.axis_2d = axis_2d

    def is_applicable_to(self, datasource: DataSource) -> bool:
        return datasource.shape >= self.kernel_shape

    @property
    def channel_multiplier(self) -> int:
        "Number of channels emited by this feature extractor for each input channel"
        return 1

    def get_expected_roi(self, data_interval: Interval5D) -> Interval5D:
        num_input_channels = data_interval.shape.c
        expected_span_c = (
            data_interval.c[0] * self.channel_multiplier,
            (data_interval.c[0] + num_input_channels) * self.channel_multiplier
        )
        return data_interval.updated(c=expected_span_c)

    #FIXME: use get_expected_roi instead
    def get_expected_shape(self, input_shape: Shape5D) -> Shape5D:
        return input_shape.updated(c=input_shape.c * self.channel_multiplier)

    def compute_into(self, roi: DataRoi, out: FeatureData) -> FeatureData:
        in_step: Shape5D = roi.shape.updated(c=1, t=1)  # compute features independently for each c and each t
        if self.axis_2d:
            in_step = in_step.updated(**{self.axis_2d: 1})  # also compute in 2D slices
        out_step: Shape5D = in_step.updated(c=self.channel_multiplier)

        for slc_in, slc_out in zip(roi.split(in_step), out.split(out_step)):
            self._compute_slice(slc_in, out=slc_out)
        return out

    @abstractmethod
    def _compute_slice(self, source_roi: DataRoi, out: FeatureData):
        pass


class FeatureExtractorCollection(FeatureExtractor):
    def __init__(self, extractors: Iterable[FeatureExtractor]):
        self.extractors = tuple(extractors)
        assert len(self.extractors) > 0

        shape_params = {}
        for label in Point5D.LABELS:
            shape_params[label] = max(f.kernel_shape[label] for f in extractors)
        self._kernel_shape = Shape5D(**shape_params)

    def get_expected_dtype(self, input_dtype: np.dtype) -> np.dtype:
        #FIXME: what if one of the feature extractors outputs a different dtype?
        return self.extractors[0].get_expected_dtype(input_dtype)

    def __repr__(self):
        return f"<{self.__class__.__name__} {[repr(f) for f in self.extractors]}>"

    @property
    def kernel_shape(self):
        return self._kernel_shape

    #FIXME: use get_expected_roi instead
    def get_expected_shape(self, input_shape: Shape5D) -> Shape5D:
        expected_c = sum(fx.get_expected_shape(input_shape).c for fx in self.extractors)
        return input_shape.updated(c=expected_c)

    def compute_into(self, roi: DataRoi, out: FeatureData) -> FeatureData:
        assert out.shape == self.get_expected_shape(roi.shape)

        channel_offset: int = out.interval.start.c

        for fx in self.extractors:
            results = fx.compute(roi).translated(Point5D.zero(c=channel_offset))
            out.set(results)
            channel_offset += results.shape.c
        return out
