from abc import ABC, abstractmethod
from typing import Tuple, List, Union, Dict, cast, Mapping
from webilastik.operator import Operator
import ndstructs
from ndstructs import array5D

import numpy as np
import vigra
from ndstructs import Array5D, Point5D, ScalarData
from ndstructs.point5D import SPAN
from ndstructs.datasource import DataSource, DataRoi

from webilastik.connected_components import ConnectedComponentsExtractor


def array5d_to_vigra(arr: Array5D, axiskeys: str):
    return vigra.taggedView(arr.raw(axiskeys), axistags=axiskeys)


class ObjectFeatureExtractor(Operator[Tuple[DataRoi, ConnectedComponentsExtractor], Array5D]):
    pass

class VigraObjectFeatureExtractor(ObjectFeatureExtractor):
    def __init__(self, feature_names: List[str]):
        super().__init__()
        self.feature_names = feature_names

    def __hash__(self) -> int:
        return hash(self.feature_names)

    def __eq__(self, other: "VigraObjectFeatureExtractor") -> bool:
        return self.feature_names == other.feature_names

    def get_halo(self) -> Point5D:
        return Point5D.zero() # FIXME: actually figure out how much halo self.feature_names needs

    def get_feature_map(self, roi: DataRoi):
        pass

    #@lru_cache()
    def compute(self, roi: Tuple[DataRoi, ConnectedComponentsExtractor]) -> Array5D:
        data_roi, components_extractor = roi
        # some object features might need more context around the object mask, which is why it gets enlarged here
        connected_comps = components_extractor.compute(data_roi).enlarged(radius=self.get_halo(), limits=data_roi.full())
        data = data_roi.datasource.retrieve(connected_comps.interval.updated(c=data_roi.c))
        timewise_features: List[Array5D] = []
        data_frames = data.split(data.shape.updated(t=1))
        label_frames = connected_comps.split(connected_comps.shape.updated(t=1))
        frame_axes = "xyzc"
        for data_frame, label_frame in zip(data_frames, label_frames):
            stats: Dict[str, Union[float, np.ndarray]] = vigra.analysis.extractRegionFeatures(
                array5d_to_vigra(data_frame, axiskeys=frame_axes).astype(np.float32),
                array5d_to_vigra(label_frame, axiskeys=frame_axes).astype(np.uint32),
                features=self.feature_names,
                ignoreLabel=0,
            )
            # good_indices = [i for i, val in enumerate(stats["Count"]) if val != 0]

            frame_features: List[Array5D] = []
            for feature_name in self.feature_names:
                clean_raw = cast(np.ndarray, stats[feature_name])  # [good_indices]
                assert isinstance(clean_raw, np.ndarray)
                xc_shape : Tuple[int, int] = (clean_raw.shape[0], int(np.prod(clean_raw.shape[1:])))
                frame_features.append(Array5D(clean_raw.reshape(xc_shape), axiskeys="xc"))

            timewise_features.append(Array5D.from_stack(frame_features, stack_along="c"))

        return Array5D.from_stack(timewise_features, stack_along="t")


[
    "Central<PowerSum<2> >",
    "Central<PowerSum<3> >",
    "Central<PowerSum<4> >",
    "Coord<ArgMaxWeight >",
    "Coord<ArgMinWeight >",
    "Coord<DivideByCount<Principal<PowerSum<2> > > >",
    "Coord<Maximum >",
    "Coord<Minimum >",
    "Coord<PowerSum<1> >",
    "Coord<Principal<Kurtosis > >",
    "Coord<Principal<PowerSum<2> > >",
    "Coord<Principal<PowerSum<3> > >",
    "Coord<Principal<PowerSum<4> > >",
    "Coord<Principal<Skewness > >",
    "Count",
    "Global<Maximum >",
    "Global<Minimum >",
    "Histogram",
    "Kurtosis",
    "Maximum",
    "Mean",
    "Minimum",
    "Quantiles",
    "RegionAxes",
    "RegionCenter",
    "RegionRadii",
    "Skewness",
    "Sum",
    "Variance",
    "Weighted<Coord<DivideByCount<Principal<PowerSum<2> > > > >",
    "Weighted<Coord<PowerSum<1> > >",
    "Weighted<Coord<Principal<Kurtosis > > >",
    "Weighted<Coord<Principal<PowerSum<2> > > >",
    "Weighted<Coord<Principal<PowerSum<3> > > >",
    "Weighted<Coord<Principal<PowerSum<4> > > >",
    "Weighted<Coord<Principal<Skewness > > >",
    "Weighted<PowerSum<0> >",
    "Weighted<RegionAxes>",
    "Weighted<RegionCenter>",
    "Weighted<RegionRadii>",
]
