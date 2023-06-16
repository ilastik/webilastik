from dataclasses import dataclass
from pathlib import PurePosixPath
import typing
from typing import Sequence, Tuple

from webilastik.server.rpc.dto import BucketFSDto, HttpFsDto, OsfsDto
from webilastik.utility.url import Url


def create_filesystem_from_message(message: "OsfsDto | HttpFsDto | BucketFSDto") -> "IFilesystem | Exception":
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


def create_filesystem_from_url(url: Url) -> "Tuple[IFilesystem, PurePosixPath] | Exception":
    if url.protocol == "file":
        from webilastik.filesystem.os_fs import OsFs
        fs_result  = OsFs.create()
        if isinstance(fs_result, Exception):
            return fs_result
        return (fs_result, url.path)
    from webilastik.filesystem.bucket_fs import BucketFs
    if BucketFs.recognizes(url):
        return BucketFs.try_from_url(url)
    from webilastik.filesystem.http_fs import HttpFs
    return HttpFs.try_from_url(url)


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
    def read_file(self, path: PurePosixPath) -> "bytes | FsIoException | FsFileNotFoundException":
        ...
    def delete(self, path: PurePosixPath) -> "None | FsIoException":
        ...
    def to_dto(self) -> "OsfsDto | HttpFsDto | BucketFSDto":
        ...
    def geturl(self, path: PurePosixPath) -> Url:
        ...
    def exists(self, path: PurePosixPath) -> "bool | FsIoException":
        listing_result = self.list_contents(path.parent)
        if isinstance(listing_result, Exception):
            return listing_result
        return path in listing_result.files or path in listing_result.directories

@dataclass
class FsDirectoryContents:
    files: Sequence[PurePosixPath]
    directories: Sequence[PurePosixPath]
