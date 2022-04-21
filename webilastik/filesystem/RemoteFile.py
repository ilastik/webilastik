from _typeshed import ReadableBuffer
import io
from typing import Callable


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
