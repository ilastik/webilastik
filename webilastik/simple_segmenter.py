
from typing import Any, Final, List, Optional, Tuple
import numpy as np
from ndstructs.array5D import Array5D
from ndstructs.point5D import Interval5D, Shape5D

from webilastik.datasource import DataRoi, DataSource
from webilastik.operator import OpRetriever, Operator


class SimpleSegmenter(Operator[DataRoi, Array5D]):
    def __init__(
        self,
        *,
        preprocessor: Operator[DataRoi, Array5D] = OpRetriever(),
        channel_index: int,
    ) -> None:
        super().__init__()
        self.preprocessor = preprocessor
        self.channel_index = channel_index

    def __hash__(self) -> int:
        return hash((self.channel_index, )) #FIXME: hash preprocessor as well?

    def __call__(self, /,  roi: DataRoi) -> Array5D:
        data = self.preprocessor(roi)
        winning_channel_indices = Array5D(
            arr=np.argmax(data.raw(data.axiskeys), axis=data.axiskeys.index("c")),
            axiskeys=data.axiskeys.replace("c", ""),
            location=roi.start,
        )

        class_seg = Array5D.allocate(data.interval.updated(c=(0,3)), dtype=np.dtype("uint8"), value=0)
        red_channel = class_seg.cut(c=0)
        raw_segmentation = (winning_channel_indices.raw("tzyx") == self.channel_index).astype(np.dtype("uint8")) * 255
        red_channel.raw("tzyx")[...] = raw_segmentation
        return class_seg

class SimpleSegmenterDataSource(DataSource):
    def __init__(
        self,
        *,
        upstream_source: DataSource,
        segmenter: SimpleSegmenter,
    ):
        self.upstream_source: Final[DataSource] = upstream_source
        self.segmenter: Final[SimpleSegmenter] = segmenter
        super().__init__(
            tile_shape=upstream_source.tile_shape.updated(c=3),
            dtype=np.dtype("uint8"),
            interval=upstream_source.interval.updated(c=(0,3)),
            spatial_resolution=upstream_source.spatial_resolution,
        )

    # FIXME: this disables caching, but it seems like caching should be controlled on instanciation
    # rather than on class declaration
    def get_tile(self, tile: Interval5D) -> Array5D:
        return self._get_tile(tile)

    def _get_tile(self, tile: Interval5D) -> Array5D:
        return self.segmenter(DataRoi(
            datasource=self.upstream_source,
            x=tile.x,
            y=tile.y,
            z=tile.z,
            t=tile.t,
            c=tile.c,
        ))

    def __hash__(self) -> int:
        return hash((self.upstream_source, self.segmenter))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, SimpleSegmenterDataSource) and
            self.upstream_source == other.upstream_source and
            self.segmenter == other.segmenter
        )