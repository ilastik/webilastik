import numpy as np
from typing import Optional, Set

from ndstructs import Array5D, Slice5D, ScalarData
from ndstructs.datasource import DataSourceSlice

from webilastik.operator import NoopOperator, Operator



class Thresholder(Operator):
    def __init__(self, *, preprocessor: Operator = NoopOperator(), threshold: float):
        self.preprocessor = preprocessor
        self.threshold = threshold

    def compute(self, roi: DataSourceSlice) -> ScalarData:
        data : Array5D = self.preprocessor.compute(roi)
        return data.threshold(self.threshold)

    def get_expected_dtype(self, input_dtype: np.dtype) -> np.dtype:
        return np.dtype("bool")

    def get_expected_roi(self, data_slice: Slice5D) -> Slice5D:
        return data_slice
