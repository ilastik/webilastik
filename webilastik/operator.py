from abc import ABC, abstractmethod
from typing import Callable, Generic, Optional, Type, TypeVar

import numpy as np

from ndstructs.datasource import DataRoi, DataSource
from ndstructs import Array5D, Shape5D

IN = TypeVar("IN")
OUT = TypeVar("OUT", covariant=True)

class Operator(ABC, Generic[IN, OUT]):
    @abstractmethod
    def compute(self, roi: IN) -> OUT:
        """Perform this operator's computaion and returns its result"""
        pass
