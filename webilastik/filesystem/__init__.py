from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import typing
from typing import Final, List, Literal, Optional, Sequence, Union, runtime_checkable
from typing_extensions import TypeAlias

from aiohttp.web import delete

from ndstructs.utils.json_serializable import IJsonable, JsonValue, ensureJsonObject, ensureJsonString
from fs.base import FS
from webilastik.server.rpc.dto import BucketFSDto, HttpFsDto, OsfsDto
from webilastik.utility.url import Url

class Filesystem(FS):
    @staticmethod
    def create_from_message(message: "OsfsDto | HttpFsDto | BucketFSDto") -> "Filesystem":
        from .http_fs import HttpFs
        from .osfs import OsFs
        from .bucket_fs import BucketFs

        # FIXME: Maybe register these via __init_subclass__?
        if isinstance(message, HttpFsDto):
            return HttpFs.from_dto(message)
        if isinstance(message, OsfsDto):
            return OsFs.from_dto(message)
        if isinstance(message, BucketFSDto):
            return BucketFs.from_dto(message)

    @abstractmethod
    def to_dto(self) -> "OsfsDto | HttpFsDto | BucketFSDto":
        pass

    @staticmethod
    def from_url(url: Url) -> "Filesystem | Exception":
        from webilastik.filesystem.osfs import OsFs
        from webilastik.filesystem.bucket_fs import BucketFs
        from webilastik.filesystem.http_fs import HttpFs

        if url.protocol == "file":
            return OsFs(url.path.as_posix())
        if url.raw.startswith(BucketFs.API_URL.raw):
            return BucketFs.try_from_url(url=url)
        return HttpFs.try_from_url(url)


#########################################333

class FileNotFoundException(Exception):
    def __init__(self, path: PurePosixPath) -> None:
        super().__init__(f"File not found: {path}")

class FsIoException(Exception):
    pass

#####################################

class IFsDirectory(typing.Protocol):
    @classmethod
    def create(cls, path: PurePosixPath) -> "IFsDirectory | FsIoException":
        ...
    def list_contents(self) -> "IFsDirectoryContents | FsIoException":
        ...
    def create_file(self, *, path: PurePosixPath, contents: bytes) -> "IFsFile | FsIoException":
        ...
    def create_directory(self, path: PurePosixPath) -> "IFsDirectory | FsIoException":
        ...
    def delete(self) -> "None | FsIoException":
        ...

class IFsFile(typing.Protocol):
    def write(self, data: bytes) -> "None | FsIoException":
        ...
    def read(self) -> "bytes | FsIoException":
        ...
    def delete(self) -> "None | FsIoException":
        ...

class IFsDirectoryContents(typing.Protocol):
    files: Sequence[IFsFile]
    directories: Sequence[IFsDirectory]


######################################
class SystemDirectory(IFsDirectory):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path

    @classmethod
    def create(cls, path: PurePosixPath) -> "SystemDirectory | FsIoException":
        system_path = Path(path)
        if not Path(path).is_dir():
            return FsIoException(f"Path is not a dir: {path}")
        return SystemDirectory(path=system_path)

    def list_contents(self) -> "SystemDirectoryContents | FsIoException":
        files: List[SystemFile] = []
        directories: List[SystemDirectory] = []
        try:
            for path in self.path.iterdir():
                if path.is_dir():
                    directories.append(SystemDirectory(path))
                else:
                    files.append(SystemFile(path))
            return SystemDirectoryContents(files=files, directories=directories)
        except Exception as e:
            return FsIoException(e)

    def create_file(self, *, path: PurePosixPath, contents: bytes) -> "SystemFile | FsIoException":
        file_path = self.path.joinpath(path.as_posix().lstrip("/"))
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()
        except Exception as e:
            return FsIoException(e)
        return SystemFile(file_path)

    def create_directory(self, path: PurePosixPath) -> "SystemDirectory | FsIoException":
        dir_path = self.path.joinpath(path.as_posix().lstrip("/"))
        try:
            dir_path.mkdir()
        except Exception as e:
            return FsIoException(e)
        return SystemDirectory(dir_path)

    def delete(self) -> "None | FsIoException":
        import shutil
        try:
            shutil.rmtree(self.path)
        except Exception as e:
            return FsIoException(e)

class SystemFile(IFsFile):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path

    def write(self, data: bytes) -> "None | FsIoException":
        try:
            with self.path.open("wb") as f:
                _ = f.write(data)
        except Exception as e:
            return FsIoException(e)

    def read(self) -> "bytes | FsIoException":
        try:
            with self.path.open("rb") as f:
                return f.read()
        except Exception as e:
            return FsIoException(e)

    def delete(self) -> "None | FsIoException":
        try:
            self.path.unlink()
        except Exception as e:
            return FsIoException(e)

class SystemDirectoryContents(IFsDirectoryContents):
    def __init__(self, files: Sequence[SystemFile], directories: Sequence["SystemDirectory"]) -> None:
        super().__init__()
        self.files = files
        self.directories = directories

########################################################\
import requests

class HttpFsDirectory(IFsDirectory):
    def __init__(self, base: Url, path: PurePosixPath, session: Optional[requests.Session] = None) -> None:
        super().__init__()
        self.base: Final[Url] = base
        self.path: Final[PurePosixPath] = path
        self.session: Final[requests.Session] = session or requests.Session()

    @classmethod
    def create(cls, path: )

    def list_contents(self) -> "HttpDirectoryContents | FsIoException":
        return FsIoException("Can't reliably list contents of http dir yet")

    def create_file(self, name: str) -> "HttpFsFile | FsIoException":
        file_path = self.path.joinpath(name.lstrip("/").lstrip("\\"))
        return HttpFsFile(base=self.base, path=file_path, session=self.session)

    def create_directory(self, name: str) -> "HttpFsDirectory | FsIoException":
        file_path = self.path.joinpath(name.lstrip("/").lstrip("\\"))
        return HttpFsDirectory(base=self.base, path=file_path, session=self.session)

    def delete(self) -> "None | FsIoException":
        try:
            response = self.session.delete(url=self.base.joinpath(self.path).raw)
            if not response.ok:
                return FsIoException(response.text)
        except Exception as e:
            return FsIoException(e)

class HttpFsFile(IFsFile):
    def __init__(self, base: Url, path: PurePosixPath, session: requests.Session) -> None:
        super().__init__()
        self.base: Final[Url] = base
        self.path: Final[PurePosixPath] = path
        self.session: Final[requests.Session] = session

    def write(self, data: bytes) -> "None | FsIoException":
        try:
            response = self.session.post(
                url=self.base.joinpath(self.path).raw,
                data=data,
            )
            if not response.ok:
                return FsIoException(response.text)
        except Exception as e:
            return FsIoException(e)

    def read(self) -> "bytes | FsIoException":
        try:
            response = self.session.get(
                url=self.base.joinpath(self.path).raw,
            )
            if not response.ok:
                return FsIoException(response.text)
            return response.content
        except Exception as e:
            return FsIoException(e)

    def delete(self) -> "None | FsIoException":
        try:
            response = self.session.delete(url=self.base.joinpath(self.path).raw)
            if not response.ok:
                return FsIoException(response.text)
        except Exception as e:
            return FsIoException(e)

class HttpDirectoryContents(IFsDirectoryContents):
    def __init__(self, files: Sequence[SystemFile], directories: Sequence["SystemDirectory"]) -> None:
        super().__init__()
        self.files = files
        self.directories = directories