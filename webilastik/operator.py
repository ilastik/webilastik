from typing import Protocol, TypeVar

from webilastik.datasource import DataRoi
from ndstructs.array5D import Array5D

IN = TypeVar("IN", contravariant=True)
OUT = TypeVar("OUT", covariant=True)

class Operator(Protocol[IN, OUT]):
    def __call__(self, /, input: IN) -> OUT: ...

class OpRetriever(Operator[DataRoi, Array5D]):
    def __init__(self, axiskeys_hint: str = "ctzyx") -> None:
        self.axiskeys_hint = axiskeys_hint
        super().__init__()
    def __call__(self, /, roi: DataRoi) -> Array5D:
        return roi.retrieve(axiskeys_hint=self.axiskeys_hint)
