from typing import Literal, Optional, Mapping, Final, Tuple, List
from pathlib import PurePosixPath
import time

import requests
from ndstructs.utils.json_serializable import ensureJsonArray, ensureJsonObject, ensureJsonString

from webilastik.filesystem import IFilesystem, FsIoException, FsFileNotFoundException, FsDirectoryContents
from webilastik.utility.url import Url
from webilastik.server.rpc.dto import BucketFSDto
from webilastik.utility import Seconds



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