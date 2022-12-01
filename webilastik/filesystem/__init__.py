from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import typing
from typing import Final, List, Literal, Optional, Sequence, Union

from fs.base import FS
from ndstructs.utils.json_serializable import ensureJsonArray, ensureJsonObject, ensureJsonString
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

class IFilesystem(typing.Protocol):
    def list_contents(self, path: PurePosixPath) -> "FsDirectoryContents | FsIoException":
        ...
    def create_file(self, *, path: PurePosixPath, contents: bytes) -> "None | FsIoException":
        ...
    def create_directory(self, path: PurePosixPath) -> "None | FsIoException":
        ...
    def read_file(self, path: PurePosixPath) -> "bytes | FsIoException":
        ...
    def delete(self, path: PurePosixPath) -> "None | FsIoException":
        ...

@dataclass
class FsDirectoryContents:
    files: Sequence[PurePosixPath]
    directories: Sequence[PurePosixPath]

######################################
class SystemFs(IFilesystem):
    @classmethod
    def from_dto(cls, dto: OsfsDto) -> "SystemFs":
        return SystemFs()

    def list_contents(self, path: PurePosixPath) -> "FsDirectoryContents | FsIoException":
        files: List[PurePosixPath] = []
        directories: List[PurePosixPath] = []
        try:
            for child in Path(path).iterdir():
                if child.is_dir():
                    directories.append(PurePosixPath(child))
                else:
                    files.append(PurePosixPath(child))
            return FsDirectoryContents(files=files, directories=directories)
        except Exception as e:
            return FsIoException(e)

    def create_file(self, *, path: PurePosixPath, contents: bytes) -> "None | FsIoException":
        file_path = Path(path)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("wb") as f:
                _ = f.write(contents)
        except Exception as e:
            return FsIoException(e)

    def create_directory(self, path: PurePosixPath) -> "None | FsIoException":
        dir_path = Path(path)
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return FsIoException(e)

    def read_file(self, path: PurePosixPath) -> "bytes | FsIoException":
        try:
            with open(path, "rb") as f:
                return f.read()
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

########################################################\
import requests

class HttpFs(IFilesystem):
    def __init__(self, base: Url, session: Optional[requests.Session] = None) -> None:
        super().__init__()
        self.base: Final[Url] = base
        self.session: Final[requests.Session] = session or requests.Session()

    @classmethod
    def from_dto(cls, dto: HttpFsDto) -> "HttpFs":
        return HttpFs(
            base=Url(
                protocol=dto.protocol,
                hostname=dto.hostname,
                path=PurePosixPath(dto.path),
                port=dto.port,
                search=dto.search,
            ),
        )

    def list_contents(self, path: PurePosixPath) -> "FsDirectoryContents | FsIoException":
        return FsIoException("Can't reliably list contents of http dir yet")

    def create_file(self, *, path: PurePosixPath, contents: bytes) -> "None | FsIoException":
        try:
            response = self.session.post(
                url=self.base.joinpath(path).raw,
                data=contents,
            )
            if not response.ok:
                return FsIoException(response.text)
        except Exception as e:
            return FsIoException(e)

    def create_directory(self, path: PurePosixPath) -> "None | FsIoException":
        return None

    def read_file(self, path: PurePosixPath) -> "bytes | FsIoException":
        try:
            response = self.session.get(
                url=self.base.joinpath(path).raw,
            )
            if not response.ok:
                return FsIoException(response.text)
            return response.content
        except Exception as e:
            return FsIoException(e)

    def delete(self, path: PurePosixPath) -> "None | FsIoException":
        try:
            response = self.session.delete(url=self.base.joinpath(path).raw)
            if not response.ok:
                return FsIoException(response.text)
        except Exception as e:
            return FsIoException(e)




class DataProxySession:
    def __init__(self) -> None:
        self.requests_session = requests.Session()
        super().__init__()

    def _do_request(self, method: Literal["get", "put", "delete"], url: Url, refresh_on_401: bool = True) -> "requests.Response | Exception":
        from webilastik.libebrains import global_user_login

        try:
            out = self.requests_session.request(
                url=url.schemeless_raw,
                method=method,
                headers=global_user_login.get_global_login_token().as_auth_header()
            )
        except Exception as e:
            return e
        if out.ok:
            return out
        if out.status_code != 401 or not refresh_on_401:
            return FsIoException(out.text)
        print(f"Asking to refresh token in BucketFS.........................")
        refreshed_token = global_user_login.refresh_global_login_token()
        if isinstance(refreshed_token, Exception):
            return refreshed_token
        print(f"Successfully refreshed token in BucketFS...................")
        return self._do_request(method=method, url=url, refresh_on_401=False)

    def get(self, url: Url) -> "requests.Response | Exception":
        return self._do_request("get", url)

    def put(self, url: Url) -> "requests.Response | Exception":
        return self._do_request("put", url)

    def delete(self, url: Url) -> "requests.Response | Exception":
        return self._do_request("delete", url)

def _safe_request(
    session: requests.Session, method: Literal["get", "put", "delete"], url: Url, data: Optional[bytes] = None
) -> "bytes | Exception":
    try:
        response = session.request(method=method, url=url.raw, data=data)
        if not response.ok:
            return Exception(response.text)
        return response.content
    except Exception as e:
        return e


class BucketFs(IFilesystem):
    API_URL = Url(protocol="https", hostname="data-proxy.ebrains.eu", path=PurePosixPath("/api/v1/buckets"))

    def __init__(
        self, bucket_name: str, session: Optional[DataProxySession] = None, cscs_session: Optional[requests.Session] = None
    ):
        self.bucket_name = bucket_name
        self.url = self.API_URL.concatpath(bucket_name)
        self.session = session or DataProxySession()
        self.cscs_session = cscs_session or requests.Session()
        super().__init__()

    @classmethod
    def from_dto(cls, dto: BucketFSDto) -> "BucketFs":
        return BucketFs(
            bucket_name=dto.bucket_name,
        )

    def list_contents(self, path: PurePosixPath, limit: Optional[int] = 50) -> "FsDirectoryContents | FsIoException":
        list_objects_path = self.url.updated_with(extra_search={
            "delimiter": "/",
            "prefix": "" if path.as_posix() == "/" else path.as_posix().lstrip("/").rstrip("/") + "/",
            "limit": str(limit)
        })
        response = self.session.get(list_objects_path)
        if isinstance(response, Exception):
            raise FsIoException(response)
        payload_obj = ensureJsonObject(response.json()) #FIXME: use DTOs everywhere?
        raw_objects = ensureJsonArray(payload_obj.get("objects"))

        files: List[PurePosixPath] = []
        directories: List[PurePosixPath] = []
        for raw_obj in raw_objects:
            obj = ensureJsonObject(raw_obj)
            path = PurePosixPath("/") / ensureJsonString(obj.get("name")) #FIXME: Use DTO ?
            if "subdir" in obj:
                directories.append(path)
            else:
                files.append(path)
        return FsDirectoryContents(files=files, directories=directories)

    def create_file(self, *, path: PurePosixPath, contents: bytes) -> "None | FsIoException":
        response = self.session.put(self.url.concatpath(path))
        if isinstance(response, Exception):
            return FsIoException(response)
        response_obj = ensureJsonObject(response.json())
        cscs_url = Url.parse_or_raise(ensureJsonString(response_obj.get("url"))) #FIXME: could raise
        response = _safe_request(self.cscs_session, method="put", url=cscs_url, data=contents)
        if isinstance(response, Exception):
            return FsIoException(response)
        return None

    def create_directory(self, path: PurePosixPath) -> "None | FsIoException":
        return None

    def read_file(self, path: PurePosixPath) -> "bytes | FsIoException":
        file_url = self.url.concatpath(path).updated_with(extra_search={"redirect": "false"})
        data_proxy_response = self.session.get(file_url)
        if isinstance(data_proxy_response, Exception):
            return FsIoException(data_proxy_response) # FIXME: return instead of raising?
        cscs_url = Url.parse_or_raise(data_proxy_response.json()["url"]) #FIXME: could raise
        cscs_response = _safe_request(self.cscs_session, method="get", url=cscs_url)
        if isinstance(cscs_response, Exception):
            return FsIoException(cscs_response)
        return cscs_response

    def delete(self, path: PurePosixPath) -> "None | FsIoException":
        dir_contents_result = self.list_contents(path.parent)
        if isinstance(dir_contents_result, Exception):
            return dir_contents_result
        if path in dir_contents_result.files:
            response = self.session.delete(self.url.concatpath(path))
            if isinstance(response, Exception):
                return FsIoException(response)
        elif path in dir_contents_result.directories:
            return FsIoException("Can't delete directories yet. Use the Data-Proxy GUI for now")
        else:
            return FsIoException("Not found")
