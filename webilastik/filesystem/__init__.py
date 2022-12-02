from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import typing
from typing import Final, List, Literal, Optional, Sequence, Mapping, Tuple
import requests
import time

from ndstructs.utils.json_serializable import ensureJsonArray, ensureJsonObject, ensureJsonString
from webilastik.server.rpc import DataTransferObject
from webilastik.server.rpc.dto import BucketFSDto, HttpFsDto, OsfsDto
from webilastik.utility.url import Url
from webilastik.utility import Seconds


def create_filesystem_from_message(message: "OsfsDto | HttpFsDto | BucketFSDto") -> "IFilesystem":
    # FIXME: Maybe register these via __init_subclass__?
    if isinstance(message, HttpFsDto):
        return HttpFs.from_dto(message)
    if isinstance(message, OsfsDto):
        return OsFs.from_dto(message)
    if isinstance(message, BucketFSDto):
        return BucketFs.from_dto(message)


def create_filesystem_from_url(url: Url) -> "Tuple[IFilesystem, PurePosixPath] | Exception":
    if url.protocol == "file":
        return (OsFs(), url.path)
    if BucketFs.recognizes(url):
        return BucketFs.try_from_url(url)
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
        listing_result = self.list_contents(path)
        if isinstance(listing_result, Exception):
            return listing_result
        return path in listing_result.files or path in listing_result.directories

@dataclass
class FsDirectoryContents:
    files: Sequence[PurePosixPath]
    directories: Sequence[PurePosixPath]

######################################
class OsFs(IFilesystem):
    @classmethod
    def from_dto(cls, dto: OsfsDto) -> "OsFs":
        return OsFs()

    def to_dto(self) -> OsfsDto:
        return OsfsDto()

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

    def read_file(self, path: PurePosixPath) -> "bytes | FsIoException | FsFileNotFoundException":
        try:
            with open(path, "rb") as f:
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

########################################################\

class HttpFs(IFilesystem):
    def __init__(
        self,
        *,
        protocol: Literal["http", "https"],
        hostname: str,
        path: PurePosixPath,
        port: Optional[int] = None,
        search: Optional[Mapping[str, str]] = None,
        session: Optional[requests.Session] = None
    ) -> None:
        super().__init__()
        self.protocol: Literal["http", "https"] = protocol
        self.base: Final[Url] = Url(
            protocol=protocol,
            hostname=hostname,
            path=path,
            port=port,
            search=search,
        )
        self.session: Final[requests.Session] = session or requests.Session()

    @classmethod
    def try_from_url(cls, url: Url) -> "Tuple[HttpFs, PurePosixPath] | Exception":
        if url.protocol not in ("http", "https"):
            return Exception(f"Bad url for HttpFs: {url}")
        return (
            HttpFs(
                protocol=url.protocol,
                hostname=url.hostname,
                port=url.port,
                path=PurePosixPath("/"),
                search=url.search,
            ),
            url.path
        )

    @classmethod
    def from_dto(cls, dto: HttpFsDto) -> "HttpFs":
        return HttpFs(
            protocol=dto.protocol,
            hostname=dto.hostname,
            path=PurePosixPath(dto.path),
            port=dto.port,
            search=dto.search,
        )

    def to_dto(self) -> HttpFsDto:
        return HttpFsDto(
            protocol=self.protocol,
            hostname=self.base.hostname,
            path=self.base.path.as_posix(),
            port=self.base.port,
            search=self.base.search,
        )

    def list_contents(self, path: PurePosixPath) -> "FsDirectoryContents | FsIoException":
        return FsIoException("Can't reliably list contents of http dir yet")

    def create_file(self, *, path: PurePosixPath, contents: bytes) -> "None | FsIoException":
        try:
            response = self.session.post(
                url=self.base.concatpath(path).raw,
                data=contents,
            )
            if not response.ok:
                return FsIoException(response.text)
        except Exception as e:
            return FsIoException(e)

    def create_directory(self, path: PurePosixPath) -> "None | FsIoException":
        return None

    def read_file(self, path: PurePosixPath) -> "bytes | FsIoException | FsFileNotFoundException":
        try:
            response = self.session.get(
                url=self.base.concatpath(path).raw,
            )
            if response.status_code == 404:
                return FsFileNotFoundException(path=path)
            if not response.ok:
                return FsIoException(response.text)
            return response.content
        except Exception as e:
            return FsIoException(e)

    def delete(self, path: PurePosixPath) -> "None | FsIoException":
        try:
            response = self.session.delete(url=self.base.concatpath(path).raw)
            if not response.ok:
                return FsIoException(response.text)
        except Exception as e:
            return FsIoException(e)

    def geturl(self, path: PurePosixPath) -> Url:
        return self.base.concatpath(path)



class DataProxySession:
    def __init__(self) -> None:
        self.requests_session = requests.Session()
        super().__init__()

    def _do_request(self, method: Literal["get", "put", "delete"], url: Url, refresh_on_401: bool = True) -> "requests.Response | FsFileNotFoundException | FsIoException":
        from webilastik.libebrains import global_user_login

        try:
            out = self.requests_session.request(
                url=url.schemeless_raw,
                method=method,
                headers=global_user_login.get_global_login_token().as_auth_header()
            )
        except Exception as e:
            return FsIoException(e)
        if out.status_code == 404:
            return FsFileNotFoundException(path=url.path) #FIXME: probably bad path
        if out.ok:
            return out
        if out.status_code != 401 or not refresh_on_401:
            return FsIoException(out.text)
        print(f"Asking to refresh token in BucketFS.........................")
        refreshed_token_result = global_user_login.refresh_global_login_token()
        if isinstance(refreshed_token_result, Exception):
            return FsIoException(refreshed_token_result)
        print(f"Successfully refreshed token in BucketFS...................")
        return self._do_request(method=method, url=url, refresh_on_401=False)

    def get(self, url: Url) -> "requests.Response | FsFileNotFoundException | FsIoException":
        return self._do_request("get", url)

    def put(self, url: Url) -> "requests.Response | FsFileNotFoundException | FsIoException":
        return self._do_request("put", url)

    def delete(self, url: Url) -> "requests.Response | FsFileNotFoundException | FsIoException":
        return self._do_request("delete", url)

def _safe_request(
    session: requests.Session, method: Literal["get", "put", "delete"], url: Url, data: Optional[bytes] = None
) -> "bytes | FsFileNotFoundException | FsIoException":
    try:
        response = session.request(method=method, url=url.raw, data=data)
        if response.status_code == 404:
            return FsFileNotFoundException(path=url.path) #FIXME: path is probably inocnsistent
        if not response.ok:
            return FsIoException(response.text)
        return response.content
    except Exception as e:
        return FsIoException(e)


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
    def recognizes(cls, url: Url) -> bool:
        return url.raw.startswith(cls.API_URL.updated_with(datascheme=url.datascheme).raw)

    @classmethod
    def try_from_url(cls, url: Url) -> "Tuple[BucketFs, PurePosixPath] | Exception":
        if not cls.recognizes(url):
            return Exception(f"Url must be inside the data-proxy ({cls.API_URL}. Got {url}")
        bucket_name_part_index = len(cls.API_URL.path.parts)
        if len(url.path.parts) <= bucket_name_part_index:
            return Exception(f"Bad bucket url: {url}")
        return (
            BucketFs(bucket_name=url.path.parts[bucket_name_part_index]),
            PurePosixPath("/".join(url.path.parts[bucket_name_part_index + 1:]) or "/")
        )

    @classmethod
    def from_dto(cls, dto: BucketFSDto) -> "BucketFs":
        return BucketFs(bucket_name=dto.bucket_name)

    def to_dto(self) -> BucketFSDto:
        return BucketFSDto(bucket_name=self.bucket_name)

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
            if "subdir" in obj:
                path = PurePosixPath("/") / ensureJsonString(obj.get("subdir")) #FIXME: Use DTO ?
                directories.append(path)
            else:
                path = PurePosixPath("/") / ensureJsonString(obj.get("name")) #FIXME: Use DTO ?
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

    def read_file(self, path: PurePosixPath) -> "bytes | FsIoException | FsFileNotFoundException":
        file_url = self.url.concatpath(path).updated_with(extra_search={"redirect": "false"})
        data_proxy_response = self.session.get(file_url)
        if isinstance(data_proxy_response, Exception):
            return data_proxy_response
        cscs_url = Url.parse_or_raise(data_proxy_response.json()["url"]) #FIXME: could raise
        cscs_response = _safe_request(self.cscs_session, method="get", url=cscs_url)
        if isinstance(cscs_response, Exception):
            return cscs_response
        return cscs_response

    def delete(
        self, path: PurePosixPath, dir_wait_time: Seconds = Seconds(5), dir_wait_interval: Seconds = Seconds(0.2)
    ) -> "None | FsIoException":
        dir_contents_result = self.list_contents(path.parent)
        if isinstance(dir_contents_result, Exception):
            return dir_contents_result

        deletion_response = self.session.delete(self.url.concatpath(path))
        if isinstance(deletion_response, Exception):
            return FsIoException(deletion_response)

        if path in dir_contents_result.files:
            return None
        if path in dir_contents_result.directories:
            while dir_wait_time > Seconds(0):
                parent_contents_result = self.list_contents(path.parent)
                if isinstance(parent_contents_result, Exception):
                    return parent_contents_result
                if path not in parent_contents_result.directories:
                    return None
                time.sleep(dir_wait_interval.to_float())
                dir_wait_time -= dir_wait_interval
        # FIXME: i think this might me unreachable
        return FsIoException("Not found")

    def geturl(self, path: PurePosixPath) -> Url:
        return self.url.concatpath(path)