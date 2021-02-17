from abc import ABC, abstractmethod
from typing import Tuple, Sequence, Dict, Mapping
import enum

import numpy as np
import vigra
from ndstructs import Array5D, Point5D, ScalarData
from ndstructs.point5D import Interval5D, SPAN, Shape5D
from ndstructs.datasource import DataSource, DataRoi

from webilastik.operator import Operator
from webilastik.connected_components import ConnectedComponentsExtractor


def array5d_to_vigra(arr: Array5D, axiskeys: str):
    return vigra.taggedView(arr.raw(axiskeys), axistags=axiskeys)


def vigra_object_feature_to_array5d(raw_feature: np.ndarray) -> Array5D:
    xc_shape : Tuple[int, int] = (raw_feature.shape[0], int(np.prod(raw_feature.shape[1:])))
    return Array5D(raw_feature.reshape(xc_shape), axiskeys="xc")


class ObjectFeatureExtractor(Operator[Tuple[DataRoi, ConnectedComponentsExtractor], Array5D]):
    pass


class VigraFeatureName(enum.Enum):
    Central_PowerSum_2 = "Central<PowerSum<2> >"
    Central_PowerSum_3 = "Central<PowerSum<3> >"
    Central_PowerSum_4 = "Central<PowerSum<4> >"
    Coord_ArgMaxWeight = "Coord<ArgMaxWeight >"
    Coord_ArgMinWeight = "Coord<ArgMinWeight >"
    Coord_DivideByCount_Principal_PowerSum_2 = "Coord<DivideByCount<Principal<PowerSum<2> > > >"
    Coord_Maximum = "Coord<Maximum >"
    Coord_Minimum = "Coord<Minimum >"
    Coord_PowerSum_1 = "Coord<PowerSum<1> >"
    Coord_Principal_Kurtosis = "Coord<Principal<Kurtosis > >"
    Coord_Principal_PowerSum_2 = "Coord<Principal<PowerSum<2> > >"
    Coord_Principal_PowerSum_3 = "Coord<Principal<PowerSum<3> > >"
    Coord_Principal_PowerSum_4 = "Coord<Principal<PowerSum<4> > >"
    Coord_Principal_Skewness_ = "Coord<Principal<Skewness > >"
    Count = "Count"
    Global_Maximum = "Global<Maximum >"
    Global_Minimum = "Global<Minimum >"
    Histogram = "Histogram"
    Kurtosis = "Kurtosis"
    Maximum = "Maximum"
    Mean = "Mean"
    Minimum = "Minimum"
    Quantiles = "Quantiles"
    RegionAxes = "RegionAxes"
    RegionCenter = "RegionCenter"
    RegionRadii = "RegionRadii"
    Skewness = "Skewness"
    Sum = "Sum"
    Variance = "Variance"
    Weighted_Coord_DivideByCount_Principal_PowerSum_2 = "Weighted<Coord<DivideByCount<Principal<PowerSum<2> > > > >"
    Weighted_Coord_PowerSum_1 = "Weighted<Coord<PowerSum<1> > >"
    Weighted_Coord_Principal_Kurtosis = "Weighted<Coord<Principal<Kurtosis > > >"
    Weighted_Coord_Principal_PowerSum_2 = "Weighted<Coord<Principal<PowerSum<2> > > >"
    Weighted_Coord_Principal_PowerSum_3 = "Weighted<Coord<Principal<PowerSum<3> > > >"
    Weighted_Coord_Principal_PowerSum_4 = "Weighted<Coord<Principal<PowerSum<4> > > >"
    Weighted_Coord_Principal_Skewness = "Weighted<Coord<Principal<Skewness > > >"
    Weighted_PowerSum_0 = "Weighted<PowerSum<0> >"
    Weighted_RegionAxes = "Weighted<RegionAxes>"
    Weighted_RegionCenter = "Weighted<RegionCenter>"
    Weighted_RegionRadii = "Weighted<RegionRadii>"


class VigraObjectFeatureExtractor(ObjectFeatureExtractor):
    def __init__(self, feature_names: Sequence[VigraFeatureName]):
        super().__init__()
        self.feature_names = feature_names

    def __hash__(self) -> int:
        return hash(self.feature_names)

    def __eq__(self, other: "VigraObjectFeatureExtractor") -> bool:
        return self.feature_names == other.feature_names

    def get_halo(self) -> Point5D:
        return Point5D.zero() # FIXME: actually figure out how much halo self.feature_names needs

    #@lru_cache()
    def get_timewise_feature_map(self, spec: Tuple[DataRoi, ConnectedComponentsExtractor]) -> Mapping[Interval5D, Mapping[str, Array5D]]:
        data_roi, components_extractor = spec
        # some object features might need more context around the object mask, which is why it gets enlarged here
        connected_comps = components_extractor.compute(data_roi).enlarged(radius=self.get_halo(), limits=data_roi.full())
        data = data_roi.datasource.retrieve(connected_comps.interval.updated(c=data_roi.c))
        feature_names = [fn.value for fn in self.feature_names]

        timewise_features : Mapping[Interval5D, Dict[str, Array5D]] = {}

        # "frame" as in "movie frames", i.e., the data within a time increment
        data_frames = data.split(data.shape.updated(t=1))
        label_frames = connected_comps.split(connected_comps.shape.updated(t=1))
        frame_axes = "xyzc"
        for data_frame, label_frame in zip(data_frames, label_frames):
            raw_frame_features: Dict[str, np.ndarray] = vigra.analysis.extractRegionFeatures(
                array5d_to_vigra(data_frame, axiskeys=frame_axes).astype(np.float32),
                array5d_to_vigra(label_frame, axiskeys=frame_axes).astype(np.uint32),
                features=feature_names,
                ignoreLabel=0,
            )
            frame_features : Mapping[str, Array5D] = {
                feature_name: vigra_object_feature_to_array5d(raw_feature)
                for feature_name, raw_feature in raw_frame_features.items()
                if feature_name in feature_names
            }
            if "RegionCenter" in frame_features:
                # Update RegionCenter to reflect the fact that they are relative to the position of data_frame
                raw_region_centers = frame_features["RegionCenter"].raw("xc")
                raw_region_centers += data_frame.location.to_np(frame_axes.replace("c", ""))
            # FIXME: clamping matches the passed data_roi, but objects might be escaping it...
            timewise_features[data_frame.interval.clamped(data_roi)] = frame_features
        return timewise_features

    #@lru_cache()
    def compute(self, roi: Tuple[DataRoi, ConnectedComponentsExtractor]) -> Array5D:
        """Outputs a Array5D where shape.x is the highest label extracted from the provided DataRoi. Channels are the stacked
        channels of the features in self.feature_names"""
        feature_map = self.get_timewise_feature_map(roi)
        timewise_features = [
            Array5D.from_stack(list(frame_features.values()), stack_along="c")
            for frame_features in feature_map.values()
        ]
        return Array5D.from_stack(timewise_features, stack_along="t")
