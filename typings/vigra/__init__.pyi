from vigra.arraytypes import *
import vigra.arraytypes as arraytypes
from .__version__ import version as version
from .filters import convolve as convolve, gaussianSmoothing as gaussianSmoothing
import .analysis
from typing import Any, Optional
from vigra.impex import readImage as readImage, readVolume as readVolume
from vigra.vigranumpycore import ChunkedArrayCompressed as ChunkedArrayCompressed, ChunkedArrayFull as ChunkedArrayFull, ChunkedArrayHDF5 as ChunkedArrayHDF5, ChunkedArrayLazy as ChunkedArrayLazy, ChunkedArrayTmpFile as ChunkedArrayTmpFile, Compression as Compression, HDF5Mode as HDF5Mode

__doc__: Any

class Timer:
    name: Any = ...
    verbose: Any = ...
    def __init__(self, name: Any, verbose: bool = ...) -> None: ...
    start: Any = ...
    def __enter__(self): ...
    end: Any = ...
    interval: Any = ...
    def __exit__(self, *args: Any) -> None: ...
standardArrayType = arraytypes.VigraArray
def defaultAxistags(tagSpec: "int | str", order: "str | None" = None, noChannels: bool = False) -> AxisTags: ...


def readHDF5(filenameOrGroup: Any, pathInFile: Any, order: Optional[Any] = ...): ...
def writeHDF5(data: Any, filenameOrGroup: Any, pathInFile: Any, compression: Optional[Any] = ..., chunks: Optional[Any] = ...) -> None: ...
def gaussianDerivative(array: Any, sigma: Any, orders: Any, out: Optional[Any] = ..., window_size: float = ...): ...

CLOCKWISE: Any
COUNTER_CLOCKWISE: Any
UPSIDE_DOWN: Any
CompleteGrow: Any
KeepContours: Any
StopAtThreshold: Any

def searchfor(searchstring: Any) -> None: ...
def imshow(image: Any, show: bool = ..., **kwargs: Any): ...
def multiImshow(images: Any, shape: Any, show: bool = ...) -> None: ...
def segShow(img: Any, labels: Any, edgeColor: Any = ..., alpha: float = ..., show: bool = ..., returnImg: bool = ..., r: int = ...): ...
def nestedSegShow(img: Any, labels: Any, edgeColors: Optional[Any] = ..., scale: int = ..., show: bool = ..., returnImg: bool = ...): ...
def show() -> None: ...

MetricType: Any

def loadBSDGt(filename: Any): ...
def pmapSeeds(pmap: Any) -> None: ...

__all__ = ["analysis"]
