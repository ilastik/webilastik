from typing import Tuple, Iterable

from abc import abstractmethod, ABC
from ndstructs import Point5D, Shape5D, Slice5D, Point5D, Array5D, ScalarData
from ndstructs.datasource import DataSource, DataSourceSlice
import numpy as np
import vigra

from webilastik.features.object_feature_extractor import array5d_to_vigra, ObjectFeatureExtractor
from webilastik.classifiers.connected_components import ConnectedComponentsExtractor


class ObjectAnnotation:
    """Marks a labeled region of the datasource as belonging to class 'color' """

    def __init__(
        self,
        *,
        position: Point5D,
        color: int,
        datasource: DataSource,  # an object label is tied to the datasource
        components_extractor: ConnectedComponentsExtractor,  # and also to the method used to extract the objects
    ):
        position_roi = DataSourceSlice(datasource, **Slice5D.enclosing([position]).to_dict())
        self.data_tile = position_roi.get_tiles(datasource.tile_shape, clamp=False).__next__().clamped(datasource.shape)
        self.position = position
        self.color = color
        self.datasource = datasource
        self.components_extractor = components_extractor
        # compute connected components in constructor to prevent creation of bad annotation
        self.label = components_extractor.compute(self.data_tile).label_at(position)

    def get_feature_samples(self, feature_extractor: ObjectFeatureExtractor):
        return feature_extractor.compute(self.data_tile, self.components_extractor).linear_raw()[self.label]

    @staticmethod
    def gather_samples(
        annotations: Iterable["ObjectAnnotation"], feature_extractor: ObjectFeatureExtractor
    ) -> Tuple[np.ndarray, np.ndarray]:
        classes = [a.color for a in annotations]
        y = np.asarray(classes, dtype=np.uint32).reshape((len(classes), 1))
        X = np.asarray([a.get_feature_samples(feature_extractor) for a in annotations]).astype(np.float32)
        return (X, y)

    def show(self):
        data = self.data_tile.retrieve().cut(Slice5D.all(), copy=True)
        for axis in "xyz":
            increment = Point5D.zero(**{axis: 1})
            for pos in (self.position + increment, self.position - increment):
                if data.roi.contains(Slice5D.enclosing([pos])):
                    data.paint_point(pos, 0)
        data.paint_point(self.position, 255)
        data.show_images()
