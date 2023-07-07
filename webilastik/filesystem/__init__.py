from dataclasses import dataclass
from pathlib import PurePosixPath
import typing
from typing import Sequence, Tuple, List

from webilastik.server.rpc.dto import BucketFSDto, HttpFsDto, OsfsDto, ZipFsDto, FsDto
from webilastik.utility.url import Url


def create_filesystem_from_message(message: FsDto) -> "IFilesystem | Exception":
    # FIXME: Maybe register these via __init_subclass__?
    if isinstance(message, HttpFsDto):
        from webilastik.filesystem.http_fs import HttpFs
        return HttpFs.from_dto(message)
    if isinstance(message, OsfsDto):
        from webilastik.filesystem.os_fs import OsFs
        return OsFs.from_dto(message)
    if isinstance(message, BucketFSDto):
        from webilastik.filesystem.bucket_fs import BucketFs
        return BucketFs.from_dto(message)
    if isinstance(message, ZipFsDto):
        from webilastik.filesystem.zip_fs import ZipFs
        return ZipFs.from_dto(message)


def create_filesystem_from_url(url: Url) -> "Tuple[IFilesystem, PurePosixPath] | Exception":
    from webilastik.filesystem.zip_fs import ZipFs
    fs = ZipFs.try_from(url=url)
    if fs is not None:
        return fs

    from webilastik.filesystem.os_fs import OsFs
    fs = OsFs.try_from(url=url)
    if fs is not None:
        return fs

    from webilastik.filesystem.bucket_fs import BucketFs
    fs = BucketFs.try_from(url=url)
    if fs is not None:
        return fs

    from webilastik.filesystem.http_fs import HttpFs
    fs = HttpFs.try_from(url=url)
    if fs is not None:
        return fs

    return Exception(f"Could not open filesystem from {url}")


#########################################333

class FsFileNotFoundException(Exception):
    def __init__(self, path: PurePosixPath) -> None:
        super().__init__(f"File not found: {path}")

class FsIoException(Exception):
    pass

#####################################

class IFilesystem(typing.Protocol):
    def list_contents(self, path: PurePosixPath) -> "FsDirectoryContents | FsIoException":
        ...
    def create_file(self, *, path: PurePosixPath, contents: bytes) -> "None | FsIoException":
        ...
    def create_directory(self, path: PurePosixPath) -> "None | FsIoException":
        ...
    def read_file(self, path: PurePosixPath, offset: int = 0, num_bytes: "int | None" = None) -> "bytes | FsIoException | FsFileNotFoundException":
        ...
    def get_size(self, path: PurePosixPath) -> "int | FsIoException | FsFileNotFoundException":
        ...
    def delete(self, path: PurePosixPath) -> "None | FsIoException":
        ...
    def to_dto(self) -> FsDto:
        ...
    def geturl(self, path: PurePosixPath) -> Url:
        ...
    def exists(self, path: PurePosixPath) -> "bool | FsIoException":
        listing_result = self.list_contents(path.parent)
        if isinstance(listing_result, Exception):
            return listing_result
        return path in listing_result.files or path in listing_result.directories

    def transfer_file(self, *, source_fs: "IFilesystem", source_path: PurePosixPath, target_path: PurePosixPath) -> "None | FsIoException | FsFileNotFoundException":
        contents = source_fs.read_file(source_path)
        if isinstance(contents, Exception):
            return contents
        return self.create_file(contents=contents, path=target_path)

@dataclass
class FsDirectoryContents:
    files: List[PurePosixPath]
    directories: List[PurePosixPath]
