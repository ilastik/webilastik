# pyright: strict

from pathlib import PurePosixPath
from typing import Final, Any
from webilastik.filesystem import FsDirectoryContents, FsFileNotFoundException, FsIoException, IFilesystem, create_filesystem_from_message

import netzip # pyright: ignore [reportMissingTypeStubs]

from webilastik.server.rpc.dto import ZipFsDto
from webilastik.utility.url import Url

class _PrivateMarker:
    pass


class _FsSource(netzip.Source):

    def __init__(self, *, _marker: _PrivateMarker, fs: IFilesystem, zip_path: PurePosixPath, size: int) -> None:
        super().__init__()
        self.fs = fs
        self.zip_path = zip_path
        self._size = size

    @classmethod
    def create(cls, fs: IFilesystem, zip_path: PurePosixPath) -> "_FsSource | FsIoException | FsFileNotFoundException":
        size_result = fs.get_size(zip_path)
        if isinstance(size_result, Exception):
            raise size_result
        return _FsSource(_marker=_PrivateMarker(), fs=fs, zip_path=zip_path, size=size_result)

    def read(self, offset: int, size: int = -1) -> bytes:
        """Read the given number of bytes at the specified offset.

        If offset is negative, it is relative to the end of the source.
        If size is negative, read all remaining bytes.
        """
        if offset < 0:
            offset = max(0, self.size() + offset) # if size == 3, offset == -1 produces actual offset==2
        read_result = self.fs.read_file(self.zip_path, offset=offset, num_bytes=None if size < 0 else size)
        if isinstance(read_result, Exception):
            raise read_result
        return read_result

    def size(self) -> int:
        """Return the total number of bytes in the source.

        Implementations are highliy recommended to cache the result.
        """
        return self._size




class ZipFs(IFilesystem):
    @classmethod
    def normalize_path(cls, path: "str | PurePosixPath") -> PurePosixPath:
        return PurePosixPath("/") / path

    @classmethod
    def raw_path(cls, path: PurePosixPath) -> bytes:
        raw = path.as_posix()
        if raw[0] == "/":
            raw = raw[1:]
        return raw.encode("utf8")

    def __init__(self, _marker: _PrivateMarker, archive: netzip.Archive, source: _FsSource) -> None:
        self.archive: Final[netzip.Archive] = archive
        self.source: Final[_FsSource] = source
        super().__init__()

    @classmethod
    def create(cls, zip_file_fs: IFilesystem, zip_file_path: PurePosixPath) -> "ZipFs | FsIoException | FsFileNotFoundException":
        source_result = _FsSource.create(fs=zip_file_fs, zip_path=zip_file_path)
        if isinstance(source_result, Exception):
            return source_result
        try:
            archive = netzip.Archive(source_result)
        except Exception as e:
            return FsIoException(e)
        return ZipFs(_marker=_PrivateMarker(), archive=archive, source=source_result)

    def list_contents(self, path: PurePosixPath) -> "FsDirectoryContents | FsIoException":
        return FsIoException("Not implemented")

    def create_file(self, *, path: PurePosixPath, contents: bytes) -> "None | FsIoException":
        return FsIoException("Not implemented")

    def create_directory(self, path: PurePosixPath) -> "None | FsIoException":
        return FsIoException("Not implemented")

    def read_file(self, path: PurePosixPath, offset: int = 0, num_bytes: "int | None" = None) -> "bytes | FsIoException | FsFileNotFoundException":
        try:
            data = self.archive[path.as_posix().encode("utf8")]
        except Exception as e:
            return FsIoException(e)
        data_len = len(data)

        start = offset
        if start >= data_len:
            return FsIoException("Offset greater than data length")

        end: "int | None" = None
        if num_bytes is not None:
            end = offset + num_bytes
            if end >= data_len:
                return FsIoException("Requested range exceeds available data")

        return data[start:end]

    def get_size(self, path: PurePosixPath) -> "int | FsIoException | FsFileNotFoundException":
        raw_entry_name = self.normalize_path(path).as_posix()[1:].encode("utf8")
        entry = self.archive.files.get(raw_entry_name)
        if entry is None:
            return FsFileNotFoundException(path)
        return entry.size

    def delete(self, path: PurePosixPath) -> "None | FsIoException":
        return FsIoException("Not implemented")

    def to_dto(self) -> ZipFsDto:
        fs_dto: Any = self.source.fs.to_dto()  #FIXME: fix ZipFsDto.zip_file_fs type and remove this Any
        return ZipFsDto(zip_file_fs=fs_dto, zip_file_path=self.source.zip_path.as_posix())

    @classmethod
    def from_dto(cls, dto: ZipFsDto) -> "ZipFs | Exception":
        fs_result = create_filesystem_from_message(dto)
        if isinstance(fs_result, Exception):
            return fs_result
        path = PurePosixPath(dto.zip_file_path)
        return cls.create(zip_file_fs=fs_result, zip_file_path=path)

    def geturl(self, path: PurePosixPath) -> Url:
        return self.source.fs.geturl(self.source.zip_path).joinpath(path) #FIXME: double check this

    def exists(self, path: PurePosixPath) -> "bool | FsIoException":
        return self.raw_path(path) in self.archive.files