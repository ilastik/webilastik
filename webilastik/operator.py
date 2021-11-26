from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from webilastik.datasource import DataRoi
from ndstructs.array5D import Array5D

IN = TypeVar("IN", contravariant=True)
OUT = TypeVar("OUT", covariant=True)

class Operator(ABC, Generic[IN, OUT]):
    @abstractmethod
    def compute(self, roi: IN) -> OUT:
        """Perform this operator's computaion and returns its result"""
        pass

class OpRetriever(Operator[DataRoi, Array5D]):
    def compute(self, roi: DataRoi) -> Array5D:
        return roi.retrieve()
