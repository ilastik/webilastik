from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

from ndstructs.datasource import DataRoi
from ndstructs import Array5D


class Operator(ABC):
    @abstractmethod
    def compute(self, roi: DataRoi) -> Array5D:
        pass

    @abstractmethod
    def get_expected_dtype(self, input_dtype: np.dtype) -> np.dtype:
        pass

class NoopOperator(Operator):
    def compute(self, roi: DataRoi) -> Array5D:
        return roi.retrieve()

    def get_expected_dtype(self, input_dtype: np.dtype) -> np.dtype:
        return input_dtype