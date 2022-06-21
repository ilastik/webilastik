import pickle
import io
from typing import Callable, Any
from typing_extensions import TypeAlias
import array
import ctypes
import mmap

# copied from typeshed:
ReadOnlyBuffer: TypeAlias = bytes  # stable
# Anything that implements the read-write buffer interface.
# The buffer interface is defined purely on the C level, so we cannot define a normal Protocol
# for it (until PEP 688 is implemented). Instead we have to list the most common stdlib buffer classes in a Union.
WriteableBuffer: TypeAlias = "bytearray | memoryview | array.array[Any] | mmap.mmap | ctypes._CData | pickle.PickleBuffer"


ReadableBuffer: TypeAlias = "ReadOnlyBuffer | WriteableBuffer"  # stable


class RemoteFile(io.BytesIO):
    def __init__(self, close_callback: Callable[["RemoteFile"], None], mode: str, data: bytes):
        self._mode = mode
        self.close_callback = close_callback
        super().__init__(data)

    def write(self, __buffer: ReadableBuffer) -> int:
        if self._mode == "r":
            raise RuntimeError("This is a readonly file!")
        return super().write(__buffer)

    def close(self):
        self.close_callback(self)
        super().close()
