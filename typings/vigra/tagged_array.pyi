import numpy
from typing import Any, Optional

xrange = range

def preserve_doc(f: Any): ...

class TaggedArray(numpy.ndarray):
    def __new__(subtype: Any, shape: Any, dtype: Any = ..., buffer: Optional[Any] = ..., offset: int = ..., strides: Optional[Any] = ..., order: Optional[Any] = ..., axistags: Optional[Any] = ...): ...
    def default_axistags(self): ...
    def copy_axistags(self): ...
    def transpose_axistags(self, axes: Optional[Any] = ...): ...
    def transform_axistags(self, index: Any): ...
    __array_priority__: float = ...
    axistags: Any = ...
    def __array_finalize__(self, obj: Any) -> None: ...
    def __copy__(self, order: str = ...): ...
    def __deepcopy__(self, memo: Any): ...
    def all(self, axis: Optional[Any] = ..., out: Optional[Any] = ...): ...
    def any(self, axis: Optional[Any] = ..., out: Optional[Any] = ...): ...
    def argmax(self, axis: Optional[Any] = ..., out: Optional[Any] = ...): ...
    def argmin(self, axis: Optional[Any] = ..., out: Optional[Any] = ...): ...
    def cumsum(self, axis: Optional[Any] = ..., dtype: Optional[Any] = ..., out: Optional[Any] = ...): ...
    def cumprod(self, axis: Optional[Any] = ..., dtype: Optional[Any] = ..., out: Optional[Any] = ...): ...
    def flatten(self, order: str = ...): ...
    def max(self, axis: Optional[Any] = ..., out: Optional[Any] = ...): ...
    def mean(self, axis: Optional[Any] = ..., out: Optional[Any] = ...): ...
    def min(self, axis: Optional[Any] = ..., out: Optional[Any] = ...): ...
    def nonzero(self): ...
    def prod(self, axis: Optional[Any] = ..., dtype: Optional[Any] = ..., out: Optional[Any] = ...): ...
    def ptp(self, axis: Optional[Any] = ..., out: Optional[Any] = ...): ...
    def ravel(self, order: str = ...): ...
    def repeat(self, repeats: Any, axis: Optional[Any] = ...): ...
    def reshape(self, shape: Any, order: str = ...): ...
    def resize(self, new_shape: Any, refcheck: bool = ..., order: bool = ...): ...
    def squeeze(self): ...
    def std(self, axis: Optional[Any] = ..., dtype: Optional[Any] = ..., out: Optional[Any] = ..., ddof: int = ...): ...
    def sum(self, axis: Optional[Any] = ..., dtype: Optional[Any] = ..., out: Optional[Any] = ...): ...
    def swapaxes(self, i: Any, j: Any): ...
    def take(self, indices: Any, axis: Optional[Any] = ..., out: Optional[Any] = ..., mode: str = ...): ...
    def transpose(self, *axes: Any): ...
    def var(self, axis: Optional[Any] = ..., dtype: Optional[Any] = ..., out: Optional[Any] = ..., ddof: int = ...): ...
    @property
    def T(self): ...
    def __getitem__(self, index: Any): ...
