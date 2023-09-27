from typing import List, Final, Tuple
from pathlib import PurePosixPath, Path
import uuid
import os
from webilastik.config import WorkflowConfig

from webilastik.filesystem import IFilesystem, FsIoException, FsFileNotFoundException, FsDirectoryContents
from webilastik.utility.url import Url
from webilastik.server.rpc.dto import OsfsDto
from webilastik.utility import Seconds

class _PrivateMarker:
    pass

class OsFs(IFilesystem):
    def __init__(self, _marker: _PrivateMarker, base: Path = Path("/")) -> None:
        self.base: Final[Path] = base
        super().__init__()

    @classmethod
    def create_scratch_dir(cls) -> "OsFs | FsIoException":
        scratch_dir_path = Path(WorkflowConfig.from_env().scratch_dir) / str(uuid.uuid4())
        try:
            scratch_dir_path.mkdir(parents=True)
        except Exception as e:
            return FsIoException(e)
        return OsFs(_marker=_PrivateMarker(), base=scratch_dir_path)

    def resolve_path(self, path: PurePosixPath) -> Path:
        safe_path_parts: List[str] = []
        for comp in path.parts:
            if comp == "." or comp == "" or comp == "/":
                continue
            elif comp == ".." and len(safe_path_parts) > 0:
                _ = safe_path_parts.pop()
            else:
                safe_path_parts.append(comp)

        return self.base / "/".join(safe_path_parts)

    @classmethod
    def create(cls) -> "OsFs | Exception":
        from webilastik.config import WEBILASTIK_ALLOW_LOCAL_FS
        if os.environ.get(WEBILASTIK_ALLOW_LOCAL_FS) in ("yes", "true", "1") or WorkflowConfig.from_env().allow_local_fs:
            return OsFs(_marker=_PrivateMarker())
        return Exception("OsFs not allowed")

    @classmethod
    def from_dto(cls, dto: OsfsDto) -> "OsFs | Exception":
        return OsFs.create()

    def to_dto(self) -> OsfsDto:
        return OsfsDto()

    def list_contents(self, path: PurePosixPath) -> "FsDirectoryContents | FsIoException":
        files: List[PurePosixPath] = []
        directories: List[PurePosixPath] = []
        resolved_path = self.resolve_path(path)
        if not resolved_path.is_dir():
            return FsIoException(f"Path is not a directory: {path}")
        try:
            for child in resolved_path.iterdir():
                fixed_path = PurePosixPath("/") / child.relative_to(self.base)
                if child.is_dir():
                    directories.append(fixed_path)
                else:
                    files.append(fixed_path)
            return FsDirectoryContents(files=files, directories=directories)
        except Exception as e:
            return FsIoException(e)

    def exists(self, path: PurePosixPath) -> "bool | FsIoException":
        try:
            return self.resolve_path(path).exists()
        except Exception as e:
            return FsIoException(e)

    def create_file(self, *, path: PurePosixPath, contents: bytes) -> "None | FsIoException":
        file_path = self.resolve_path(path)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("wb", buffering=0) as f:
                _ = f.write(contents)
        except Exception as e:
            return FsIoException(e)

    def create_directory(self, path: PurePosixPath) -> "None | FsIoException":
        dir_path = self.resolve_path(path)
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return FsIoException(e)

    def read_file(self, path: PurePosixPath, offset: int = 0, num_bytes: "int | None" = None) -> "bytes | FsIoException | FsFileNotFoundException":
        file_path = self.resolve_path(path)
        try:
            with open(file_path, "rb") as f:
                _ = f.seek(offset, os.SEEK_SET if offset >= 0 else os.SEEK_END)
                return f.read(num_bytes)
        except FileNotFoundError as e:
            return FsFileNotFoundException(path=path)
        except Exception as e:
            return FsIoException(e)

    def get_size(self, path: PurePosixPath) -> "int | FsIoException | FsFileNotFoundException":
        try:
            return self.resolve_path(path).stat().st_size
        except FileNotFoundError as e:
            return FsFileNotFoundException(path)
        except Exception as e:
            return FsIoException(e)

    def delete(self, path: PurePosixPath) -> "None | FsIoException":
        import shutil
        node_path = Path(self.resolve_path(path))
        try:
            if node_path.is_dir():
                shutil.rmtree(node_path)
            else:
                node_path.unlink()
        except Exception as e:
            return FsIoException(e)

    def geturl(self, path: PurePosixPath) -> Url:
        return Url(protocol="file", hostname="localhost", path=PurePosixPath(self.resolve_path(path)))

    @classmethod
    def try_from(cls, *, url: Url) -> "Tuple[OsFs, PurePosixPath] | None | Exception":
        if not url.protocol == "file":
            return None
        fs_result  = OsFs.create()
        if isinstance(fs_result, Exception):
            return fs_result
        return (fs_result, url.path)