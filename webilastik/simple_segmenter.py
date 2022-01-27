
from typing import List
import numpy as np
from ndstructs.array5D import Array5D

from webilastik.datasource import DataRoi
from webilastik.operator import OpRetriever, Operator


class SimpleSegmenter(Operator[DataRoi, Array5D]):
    def __init__(
        self,
        *,
        preprocessor: Operator[DataRoi, Array5D] = OpRetriever(),
    ) -> None:
        super().__init__()
        self.preprocessor = preprocessor

    def compute(self, roi: DataRoi) -> Array5D:
        data = self.preprocessor.compute(roi)
        winning_channel_indices = Array5D(
            arr=np.argmax(data.raw(data.axiskeys), axis=data.axiskeys.index("c")),
            axiskeys=data.axiskeys.replace("c", ""),
            location=roi.start,
        )

        out = Array5D.allocate_like(data, dtype=np.dtype("uint8"))
        for channel_index, out_channel in enumerate(out.split(shape=winning_channel_indices.shape)):
            raw_segmentation = (winning_channel_indices.raw("tzyx") == channel_index).astype(np.dtype("uint8")) * 255
            out_channel.raw("tzyx")[...] = raw_segmentation
        return out