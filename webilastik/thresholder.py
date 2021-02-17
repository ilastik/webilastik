from ndstructs.point5D import Point5D
import numpy as np
from typing import Optional, Set

from ndstructs import Array5D, Interval5D, ScalarData
from ndstructs.datasource import DataRoi

from webilastik.operator import Operator, OpRetriever



class Thresholder(Operator[DataRoi, Array5D]):
    def __init__(self, *, threshold: float, preprocessor: Operator[DataRoi, Array5D] = OpRetriever()):
        self.preprocessor = preprocessor
        self.threshold = threshold

    def __hash__(self) -> int:
        return hash((self.preprocessor, self.threshold))

    def __eq__(self, other: "Thresholder"):
        return (self.preprocessor, self.threshold) == (other.preprocessor, other.threshold)

    def compute(self, roi: DataRoi) -> ScalarData:
        raw_data = roi.retrieve().raw(Point5D.LABELS)
        out = ScalarData.allocate(interval=roi, dtype=np.dtype("bool"))

        out.raw(Point5D.LABELS)[raw_data >= self.threshold] = True
        out.raw(Point5D.LABELS)[raw_data < self.threshold] = False
        return out
