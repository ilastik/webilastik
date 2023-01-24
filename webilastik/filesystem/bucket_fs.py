# pyright: strict

import json
from typing import Literal, Optional, Tuple, List
from pathlib import PurePosixPath
import time

import requests
from ndstructs.utils.json_serializable import ensureJsonArray, ensureJsonObject, ensureJsonString

from webilastik.filesystem import IFilesystem, FsIoException, FsFileNotFoundException, FsDirectoryContents
from webilastik.libebrains.user_credentials import EbrainsUserCredentials

from webilastik.utility.url import Url
from webilastik.server.rpc.dto import BucketFSDto
from webilastik.utility import Seconds
from webilastik.utility.request import request as safe_request, ErrRequestCrashed

_cscs_session = requests.Session()
_data_proxy_session = requests.Session()

class BucketFs(IFilesystem):
    API_URL = Url(protocol="https", hostname="data-proxy.ebrains.eu", path=PurePosixPath("/api/v1/buckets"))

    def __init__(self, bucket_name: str, ebrains_user_credentials: EbrainsUserCredentials):
        self.bucket_name = bucket_name
        self.url = self.API_URL.concatpath(bucket_name)
        self.ebrains_user_credentials = ebrains_user_credentials
        super().__init__()

    def _requests_from_data_proxy(
        self,
        method: Literal["get", "put", "delete"],
        url: Url,
        data: Optional[bytes],
        refresh_on_401: bool = True,
    ) -> "bytes | FsFileNotFoundException | Exception":
        response_result = safe_request(
            session=_data_proxy_session,
            method=method,
            url=url,
            data=data,
            headers=self.ebrains_user_credentials.user_token.as_auth_header(),
        )
        if isinstance(response_result, bytes):
            return response_result
        if isinstance(response_result, ErrRequestCrashed):
            return response_result
        if response_result.status_code == 404:
            return FsFileNotFoundException(url.path) #FIXME
        if (response_result.status_code != 401) or (not refresh_on_401):
            return response_result
        print(f"Asking to refresh token in BucketFS.........................")
        refresh_token_result = self.ebrains_user_credentials.refresh()
        if isinstance(refresh_token_result, Exception):
            return refresh_token_result
        print(f"Successfully refreshed token in BucketFS...................")
        return self._requests_from_data_proxy(method=method, url=url, data=data, refresh_on_401=False)

    @classmethod
    def recognizes(cls, url: Url) -> bool:
        return (
            url.protocol == "https" and
            url.hostname == cls.API_URL.hostname and
            url.port == cls.API_URL.port and
            url.path.as_posix().startswith(cls.API_URL.path.as_posix())
        )

    @classmethod
    def try_from_url(cls, url: Url, ebrains_user_credentials: EbrainsUserCredentials) -> "Tuple[BucketFs, PurePosixPath] | Exception":
        if not cls.recognizes(url):
            return Exception(f"Url must be inside the data-proxy ({cls.API_URL}. Got {url}")
        bucket_name_part_index = len(cls.API_URL.path.parts)
        if len(url.path.parts) <= bucket_name_part_index:
            return Exception(f"Bad bucket url: {url}")
        return (
            BucketFs(
                bucket_name=url.path.parts[bucket_name_part_index], ebrains_user_credentials=ebrains_user_credentials
            ),
            PurePosixPath("/".join(url.path.parts[bucket_name_part_index + 1:]) or "/")
        )

    @classmethod
    def from_dto(cls, dto: BucketFSDto, ebrains_user_credentials: EbrainsUserCredentials) -> "BucketFs":
        return BucketFs(bucket_name=dto.bucket_name, ebrains_user_credentials=ebrains_user_credentials)

    def to_dto(self) -> BucketFSDto:
        return BucketFSDto(bucket_name=self.bucket_name)

    def list_contents(self, path: PurePosixPath, limit: Optional[int] = 500) -> "FsDirectoryContents | FsIoException":
        list_objects_path = self.url.updated_with(extra_search={
            "delimiter": "/",
            "prefix": "" if path.as_posix() == "/" else path.as_posix().lstrip("/").rstrip("/") + "/",
            "limit": str(limit)
        })
        response = self._requests_from_data_proxy(method="get", url=list_objects_path, data=None)
        if isinstance(response, Exception):
            raise FsIoException(response)
        payload_obj = ensureJsonObject(json.loads(response)) #FIXME: use DTOs everywhere?
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
        response = self._requests_from_data_proxy(method="put", url=self.url.concatpath(path), data=None)
        if isinstance(response, Exception):
            return FsIoException(response)
        response_obj = ensureJsonObject(json.loads(response))
        cscs_url = Url.parse_or_raise(ensureJsonString(response_obj.get("url"))) #FIXME: could raise
        response = safe_request(session=_cscs_session, method="put", url=cscs_url, data=contents)
        if isinstance(response, Exception):
            return FsIoException(response)
        return None

    def create_directory(self, path: PurePosixPath) -> "None | FsIoException":
        return None

    def get_swift_object_url(self, path: PurePosixPath) -> "Url | FsIoException | FsFileNotFoundException":
        file_url = self.url.concatpath(path).updated_with(extra_search={"redirect": "false"})
        data_proxy_response = self._requests_from_data_proxy(method="get", url=file_url, data=None)
        if isinstance(data_proxy_response, FsFileNotFoundException):
            return FsFileNotFoundException(path)
        if isinstance(data_proxy_response, Exception):
            return FsIoException(data_proxy_response) # FIXME: pass exception directly into other?
        return Url.parse_or_raise(json.loads(data_proxy_response)["url"]) #FIXME: fix all raises

    def read_file(self, path: PurePosixPath) -> "bytes | FsIoException | FsFileNotFoundException":
        cscs_url_result = self.get_swift_object_url(path=path)
        if isinstance(cscs_url_result, Exception):
            return cscs_url_result
        cscs_response = safe_request(session=_cscs_session, method="get", url=cscs_url_result)
        if isinstance(cscs_response, Exception):
            return FsIoException(cscs_response) # FIXME: pass exception directly into other?
        return cscs_response

    def delete(
        self, path: PurePosixPath, dir_wait_time: Seconds = Seconds(5), dir_wait_interval: Seconds = Seconds(0.2)
    ) -> "None | FsIoException":
        dir_contents_result = self.list_contents(path.parent)
        if isinstance(dir_contents_result, Exception):
            return dir_contents_result

        deletion_response = self._requests_from_data_proxy(method="delete", url=self.url.concatpath(path), data=None)
        #FIXME: what about not found?
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