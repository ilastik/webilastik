
from typing import List
import numpy as np
from ndstructs.array5D import Array5D

from webilastik.datasource import DataRoi
from webilastik.operator import OpRetriever, Operator


class SimpleSegmenter(Operator[DataRoi, List[Array5D]]):
    def __init__(
        self,
        *,
        preprocessor: Operator[DataRoi, Array5D] = OpRetriever(),
    ) -> None:
        super().__init__()
        self.preprocessor = preprocessor

    def __call__(self, /,  roi: DataRoi) -> List[Array5D]:
        data = self.preprocessor(roi)
        winning_channel_indices = Array5D(
            arr=np.argmax(data.raw(data.axiskeys), axis=data.axiskeys.index("c")),
            axiskeys=data.axiskeys.replace("c", ""),
            location=roi.start,
        )

        segmentations: List[Array5D] = []

        for class_index in range(data.shape.c):
            class_seg = Array5D.allocate(data.interval.updated(c=(0,3)), dtype=np.dtype("uint8"), value=0)
            red_channel = class_seg.cut(c=0)
            raw_segmentation = (winning_channel_indices.raw("tzyx") == class_index).astype(np.dtype("uint8")) * 255
            red_channel.raw("tzyx")[...] = raw_segmentation
            segmentations.append(class_seg)

        return segmentations