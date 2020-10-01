from abc import ABC, abstractmethod
from typing import List, Union, Dict, cast

import numpy as np
import vigra
from ndstructs import Array5D, Point5D, ScalarData
from ndstructs.datasource import DataSource, DataSourceSlice

from webilastik.connected_components import ConnectedComponentsExtractor


def array5d_to_vigra(arr: Array5D, axiskeys: str):
    return vigra.taggedView(arr.raw(axiskeys), axistags=axiskeys)


class ObjectFeatureExtractor(ABC):
    def is_applicable_to(self, datasource: DataSource):
        return True  # FIXME

    @abstractmethod
    def compute(self, roi: DataSourceSlice, components_extractor: ConnectedComponentsExtractor) -> Array5D:
        pass


class VigraObjectFeatureExtractor(ObjectFeatureExtractor):
    def __init__(self, feature_names: List[str]):
        super().__init__()
        self.feature_names = feature_names

    @classmethod
    def get_halo(cls) -> Point5D:
        return Point5D.zero()

    def compute(
        self, roi: DataSourceSlice, components_extractor: ConnectedComponentsExtractor
    ) -> Array5D:
        connected_comps = components_extractor.compute(roi).enlarged(radius=self.get_halo(), limits=roi.full())
        data = roi.datasource.retrieve(connected_comps.roi.with_coord(c=roi.c))
        timewise_features: List[Array5D] = []
        data_frames = data.split(data.shape.with_coord(t=1))
        label_frames = connected_comps.split(connected_comps.shape.with_coord(t=1))
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
            for fname in self.feature_names:
                clean_raw = cast(np.ndarray, stats[fname])  # [good_indices]
                assert isinstance(clean_raw, np.ndarray)
                xc_shape = (clean_raw.shape[0], int(np.prod(clean_raw.shape[1:])))
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
