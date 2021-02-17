import numpy as np
from typing import Optional, Set

from skimage import measure as skmeasure
from ndstructs import Array5D, Interval5D, Shape5D, ScalarData, Point5D
from ndstructs.array5D import ARR
from ndstructs.datasource import DataRoi

from webilastik.operator import Operator, OpRetriever


class ConnectedComponents(ScalarData):
    def __init__(
        self, arr: np.ndarray, *, axiskeys: str, location: Point5D = Point5D.zero(), labels: Optional[Set[int]] = None
    ):
        super().__init__(arr, axiskeys=axiskeys, location=location)
        self._border_colors: Optional[Set[int]] = None
        self._labels = labels

    @staticmethod
    def from_array5d(data: Array5D, labels: Optional[Set[int]] = None) -> "ConnectedComponents":
        return ConnectedComponents(
            data.raw(Point5D.LABELS), axiskeys=Point5D.LABELS, location=data.location, labels=labels
        )

    def rebuild(self: ARR, arr: np.ndarray, *, axiskeys: str, location: Point5D = None) -> ARR:
        location = self.location if location is None else location
        return ConnectedComponents(arr, axiskeys=axiskeys, location=location, labels=None)  # FIXME

    def enlarged(self, radius: Point5D, limits: Interval5D) -> "ConnectedComponents":
        """Enlarges the array by 'radius', and fills this halo with zero"""
        haloed_roi = self.interval.enlarged(radius).clamped(limits)
        haloed_data = Array5D.allocate(haloed_roi, value=0, dtype=self.dtype)
        haloed_data.set(self)
        return ConnectedComponents.from_array5d(haloed_data, labels=self.labels)

    @property
    def border_colors(self) -> Set[int]:
        if self._border_colors is None:
            self._border_colors = set(self.unique_border_colors().raw("x"))
            self._border_colors.discard(0)
        return self._border_colors

    @property
    def labels(self) -> Set[int]:
        if self._labels is None:
            self._labels = set(self.unique_colors().raw("x"))
            self._labels.discard(0)
        return self._labels

    def fully_contains_objects_in(self, roi: Interval5D) -> bool:
        assert self.interval.contains(roi)
        return self.border_colors.isdisjoint(self.cut(roi).border_colors)

    def label_at(self, point: Point5D) -> int:
        point_roi = Interval5D.enclosing([point])
        if not self.interval.contains(point_roi):
            raise ValueError(f"Point {point} is not inside the labels at {self.interval}")
        label = self.cut(point_roi).raw("x")[0]
        if label == 0:
            raise ValueError(f"Point {point} is not on top of an object")
        return label

    @classmethod
    def label(cls, data: ScalarData, background: int = 0) -> "ConnectedComponents":
        assert data.shape.c == 1
        assert data.shape.t == 1  # FIXME: iterate over time frames?

        raw_axes = "xyz"
        labeled_raw, num_labels = skmeasure.label(data.raw(raw_axes), background=background, return_num=True) #type: ignore
        all_labels = set(range(1, num_labels + 1))
        return ConnectedComponents(labeled_raw, axiskeys=raw_axes, location=data.location, labels=all_labels)

    def clean(self, center_roi: Interval5D) -> "ConnectedComponents":
        """Removes (sets to 0) all connected components that have labels which are not inside center_roi"""
        center_roi_labels: Set[int] = self.cut(center_roi).labels
        labels_to_remove: Set[int] = self.labels.difference(center_roi_labels)
        labeled_raw = np.copy(self.raw(Point5D.LABELS))
        for label in labels_to_remove:
            labeled_raw[labeled_raw == label] = 0

        return ConnectedComponents(
            labeled_raw, axiskeys=Point5D.LABELS, location=self.location, labels=center_roi_labels
        )

class ConnectedComponentsExtractor(Operator[DataRoi, ConnectedComponents]):
    def __init__(
        self,
        *,
        preprocessor: Operator[DataRoi, Array5D] = OpRetriever(), #FIXME: ScalarData instead of Array5D?
        object_channel_idx: int,
        expansion_step: Optional[Shape5D] = None,
        maximum_tile_size: Optional[Shape5D] = None
    ):
        self.preprocessor = preprocessor
        self.object_channel_idx = object_channel_idx
        self.expansion_step = expansion_step
        self.maximum_tile_size = maximum_tile_size

    def __hash__(self) -> int:
        return hash((self.preprocessor, self.object_channel_idx, self.expansion_step, self.maximum_tile_size))

    def __eq__(self, other: "ConnectedComponentsExtractor") -> bool:
        return (self.preprocessor, self.object_channel_idx, self.expansion_step, self.maximum_tile_size) == \
            (other.preprocessor, other.object_channel_idx, other.expansion_step, other.maximum_tile_size)

    #@lru_cache()
    def compute(self, roi: DataRoi) -> ConnectedComponents:
        roi = roi.updated(c=self.object_channel_idx)
        expansion_step: Shape5D = (self.expansion_step or roi.tile_shape).updated(c=0)

        current_roi = roi
        while True:
            thresholded_data: ScalarData = ScalarData.fromArray5D(self.preprocessor.compute(current_roi))
            connected_comps = ConnectedComponents.label(thresholded_data)
            if connected_comps.fully_contains_objects_in(roi):
                break
            if current_roi == roi.full():
                break
            # FIXME: check mximum_tile_size too
            current_roi = current_roi.enlarged(radius=expansion_step).clamped(roi.full())
        return connected_comps.clean(roi)
