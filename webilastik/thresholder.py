from ndstructs.point5D import Point5D
import numpy as np

from ndstructs.array5D import Array5D, ScalarData
from webilastik.datasource import DataRoi

from webilastik.operator import Operator, OpRetriever



class Thresholder(Operator[DataRoi, Array5D]):
    def __init__(self, *, threshold: float, preprocessor: Operator[DataRoi, Array5D] = OpRetriever()):
        self.preprocessor = preprocessor
        self.threshold = threshold
        super().__init__()

    def __hash__(self) -> int:
        return hash((self.preprocessor, self.threshold))

    def __eq__(self, other: object):
        if not isinstance(other, Thresholder):
            return False
        return (self.preprocessor, self.threshold) == (other.preprocessor, other.threshold)

    def __call__(self, /, roi: DataRoi) -> ScalarData:
        raw_data = roi.retrieve().raw(Point5D.LABELS)
        out = ScalarData.allocate(interval=roi, dtype=np.dtype("bool"))

        out.raw(Point5D.LABELS)[raw_data >= self.threshold] = True
        out.raw(Point5D.LABELS)[raw_data < self.threshold] = False
        return ScalarData(out.raw(out.axiskeys), axiskeys=out.axiskeys, location=out.location)
