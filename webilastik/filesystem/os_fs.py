from typing import List
from pathlib import PurePosixPath, Path

from webilastik.filesystem import IFilesystem, FsIoException, FsFileNotFoundException, FsDirectoryContents
from webilastik.utility.url import Url
from webilastik.server.rpc.dto import OsfsDto
from webilastik.utility import Seconds

class _PrivateMarker:
    pass

class OsFs(IFilesystem):
    def __init__(self, _marker: _PrivateMarker) -> None:
        raise Exception("OsFs not allowed") #FIXME
        super().__init__()

    def _make_path(self, path: PurePosixPath) -> Path:
        return Path("/") / path

    @classmethod
    def create(cls) -> "OsFs | Exception":
        try:
            return OsFs(_marker=_PrivateMarker())
        except Exception as e:
            return e

    @classmethod
    def from_dto(cls, dto: OsfsDto) -> "OsFs | Exception":
        return OsFs.create()

    def to_dto(self) -> OsfsDto:
        return OsfsDto()

    def list_contents(self, path: PurePosixPath) -> "FsDirectoryContents | FsIoException":
        files: List[PurePosixPath] = []
        directories: List[PurePosixPath] = []
        try:
            for child in self._make_path(path).iterdir():
                if child.is_dir():
                    directories.append(PurePosixPath(child))
                else:
                    files.append(PurePosixPath(child))
            return FsDirectoryContents(files=files, directories=directories)
        except Exception as e:
            return FsIoException(e)

    def exists(self, path: PurePosixPath) -> "bool | FsIoException":
        return self._make_path(path).exists()

    def create_file(self, *, path: PurePosixPath, contents: bytes) -> "None | FsIoException":
        file_path = self._make_path(path)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("wb") as f:
                _ = f.write(contents)
        except Exception as e:
            return FsIoException(e)

    def create_directory(self, path: PurePosixPath) -> "None | FsIoException":
        dir_path = self._make_path(path)
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return FsIoException(e)

    def read_file(self, path: PurePosixPath) -> "bytes | FsIoException | FsFileNotFoundException":
        file_path = self._make_path(path)
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except FileNotFoundError as e:
            return FsFileNotFoundException(path=path)
        except Exception as e:
            return FsIoException(e)

    def delete(self, path: PurePosixPath) -> "None | FsIoException":
        import shutil
        node_path = Path(path)
        try:
            if node_path.is_dir():
                shutil.rmtree(node_path)
            else:
                node_path.unlink()
        except Exception as e:
            return FsIoException(e)

    def geturl(self, path: PurePosixPath) -> Url:
        return Url(protocol="file", hostname="localhost", path=path)