#pyright: strict
from typing import Tuple, Iterable, Any

from ndstructs import Point5D, Interval5D
from webilastik.datasource import DataSource, DataRoi
import numpy as np
from numpy import ndarray, dtype, uint32, float32

from webilastik.features.object_feature_extractor import ObjectFeatureExtractor
from webilastik.connected_components import ConnectedComponentsExtractor


class ObjectAnnotation:
    """Marks a labeled region of the datasource as belonging to class 'klass' """

    def __init__(
        self,
        *,
        position: Point5D, # an anchor point within datasource
        klass: int,
        datasource: DataSource,  # an object label is tied to the datasource
        components_extractor: ConnectedComponentsExtractor,  # and also to the method used to extract the objects
    ):
        position_roi = DataRoi(datasource, **Interval5D.enclosing([position]).to_dict())
        self.data_tile = position_roi.enlarge_to_tiles(tile_shape=datasource.tile_shape, tiles_origin=datasource.interval.start).clamped(datasource.interval)
        self.position = position
        self.klass = klass
        self.datasource = datasource
        self.components_extractor = components_extractor
        # compute connected components in constructor to prevent creation of bad annotation
        self.label = components_extractor(self.data_tile).label_at(position)
        super().__init__()

    def get_feature_samples(self, feature_extractor: ObjectFeatureExtractor) -> "np.ndarray[Any, Any]": #1-d array with shape (num_feature_channels,)
        return feature_extractor((self.data_tile, self.components_extractor)).linear_raw()[self.label]

    @staticmethod
    def gather_samples(
        annotations: Iterable["ObjectAnnotation"], feature_extractor: ObjectFeatureExtractor
    ) -> Tuple["ndarray[Any, dtype[float32]]", "ndarray[Any, dtype[uint32]]"]:
        classes = [a.klass for a in annotations]
        y: "ndarray[Any, dtype[uint32]]" = np.asarray(classes, dtype=uint32).reshape((len(classes), 1)) #pyright: ignore[reportUnknownMemberType]
        X: "ndarray[Any, dtype[float32]]" = np.asarray([a.get_feature_samples(feature_extractor) for a in annotations]).astype(float32) #pyright: ignore[reportUnknownMemberType]
        return (X, y)

    # def show(self):
    #     data = self.data_tile.retrieve().cut(copy=True)
    #     for axis in "xyz":
    #         increment = Point5D.zero(**{axis: 1})
    #         for pos in (self.position + increment, self.position - increment):
    #             if data.interval.contains(Interval5D.enclosing([pos])):
    #                 data.paint_point(pos, 0)
    #     data.paint_point(self.position, 255)
    #     data.show_images()
