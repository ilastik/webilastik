from _typeshed import ReadableBuffer
from typing import AnyStr, BinaryIO, List, Optional, Union
from pathlib import PurePosixPath
import io
import os

from webilastik.filesystem import FsFileNotFoundException, FsIoException, IFilesystem

class FsFileLike(BinaryIO):
    def __init__(self, fs: IFilesystem, path: PurePosixPath, size: int):
        super().__init__()
        self.fs = fs
        self.path = path
        self.position: int = 0
        self.size: int = size

    @property
    def mode(self) -> str:
        return "w+b" #FIXME: double check this

    @property
    def name(self) -> str:
        return self.fs.geturl(self.path).raw

    def close(self) -> None:
        pass

    @property
    def closed(self) -> bool:
        return False

    def fileno(self) -> int:
        return 9999 #FIXME: where could this break?

    def flush(self) -> None:
        pass

    def isatty(self) -> bool:
        return False

    def read(self, n: int = -1) -> bytes:
        result = self.fs.read_file(self.path, offset=self.position, num_bytes= n if n >=0 else None)
        if isinstance(result, FsFileNotFoundException):
            raise FileNotFoundError(self.name)
        if isinstance(result, FsIoException):
            raise BlockingIOError(self.name)
        return result

    def readable(self) -> bool:
        return True

    def readline(self, limit: int = -1) -> bytes:
        raise io.UnsupportedOperation(f"Can't read file {self.name} as text")

    def readlines(self, hint: int = -1) -> List[bytes]:
        raise io.UnsupportedOperation(f"Can't read file {self.name} as text")

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == os.SEEK_SET:
            self.position = offset
        elif whence == os.SEEK_CUR:
            self.position += offset
        elif whence == os.SEEK_END:
            size_result = self.fs.get_size(self.path)
            if isinstance(size_result, Exception):
                raise BlockingIOError(f"Could not get file size for {self.name}")
            self.position = size_result + offset
        else:
            raise ValueError(f"Bad seek whence: {whence}")

        if self.position > self.size:
            print(f"WARNING: Seeked past size. Maybe we should expand the underling file?")

        self.size = max(self.size, self.position)
        return self.position

    def seekable(self) -> bool:
        return False #FIXME: can I just get away with this?

    def tell(self) -> int:
        return self.position

    def truncate(self, size: Optional[int] = None) -> int:
        self.size = size if size is not None else self.position
        return self.size

    def writable(self) -> bool:
        return False # FIXME:  Remove this once we implement write

    def write(self, s: ReadableBuffer) -> int:
        raise BlockingIOError("Not implemented yet. Needs IFIlesystem to implement write offsets")

    def writelines(self, lines: List[AnyStr]) -> None: # pyright: ignore [reportIncompatibleMethodOverride]
        raise io.UnsupportedOperation(f"Can't write lines to binary file")




