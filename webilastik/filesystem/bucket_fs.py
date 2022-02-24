import os
from pathlib import PurePosixPath
import io
from typing import Any, Collection, Optional, Union, Dict, List
from datetime import datetime
import time

import requests
from fs.base import FS
from fs.subfs import SubFS
from fs.info import Info
from fs.errors import ResourceNotFound
from fs.permissions import Permissions
from fs.enums import ResourceType
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonInt, ensureJsonObject, ensureJsonString, ensureJsonArray
from webilastik.filesystem import JsonableFilesystem

from webilastik.filesystem.RemoteFile import RemoteFile
from webilastik.libebrains.user_token import UserToken
from webilastik.ui.usage_error import UsageError
from webilastik.utility.url import Protocol, Url


class BucketObject:
    def __init__(
        self,
        *,
        hash_: str,
        last_modified: datetime,
        bytes_: int,
        name: PurePosixPath,
        content_type: str
    ):
        self.hash = hash_
        self.last_modified = last_modified
        self.bytes = bytes_
        self.name = name
        self.content_type = content_type

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "BucketObject":
        value_dict = ensureJsonObject(value)
        return BucketObject(
            hash_ = ensureJsonString(value_dict.get("hash")),
            last_modified=datetime.fromisoformat(ensureJsonString(value_dict.get("last_modified"))),
            bytes_=ensureJsonInt(value_dict.get("bytes")),
            name=PurePosixPath(ensureJsonString(value_dict.get("name"))),
            content_type=ensureJsonString(value_dict.get("content_type")),
        )

    def to_json_value(self) -> JsonValue:
        return {
            "hash": self.hash,
            "last_modified": self.last_modified.isoformat(),
            "bytes": self.bytes,
            "name": str(self.name),
            "content_type": self.content_type,
        }

class BucketSubdir:
    def __init__(self, subdir: PurePosixPath):
        self.subdir = subdir
        # self.bytes = bytes
        # self.last_modified = last_modified
        # self.objects_count = objects_count

    @property
    def name(self) -> str:
        return str(self.subdir) + "/"

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "BucketSubdir":
        value_obj = ensureJsonObject(value)
        return BucketSubdir(
            subdir=PurePosixPath(ensureJsonString(value_obj.get("subdir")))
        )


class BucketFs(JsonableFilesystem):
    API_URL = Url(protocol=Protocol.HTTPS, hostname="data-proxy.ebrains.eu", path=PurePosixPath("/api/buckets"))

    def __init__(self, bucket_name: str, prefix: PurePosixPath, ebrains_user_token: UserToken):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.ebrains_user_token = ebrains_user_token
        self.bucket_url = self.API_URL.concatpath(bucket_name)
        self.url = self.bucket_url.concatpath(prefix)
        super().__init__()

        self.session = requests.Session()
        self.session.headers.update(ebrains_user_token.as_auth_header())
        self.cscs_session = requests.Session()
        self.pid = os.getpid()

    @classmethod
    def try_create(cls, bucket_name: str, prefix: PurePosixPath, ebrains_user_token: "UserToken | None" = None) -> "BucketFs | UsageError":
        token_result = ebrains_user_token or UserToken.get_global_login_token()
        if isinstance(token_result, UsageError):
            return token_result
        return BucketFs(bucket_name=bucket_name, prefix=prefix, ebrains_user_token=token_result)

    @classmethod
    def try_from_url(cls, url: Url, ebrains_user_token: "UserToken | None") -> "BucketFs | UsageError":
        if not url.raw.startswith(cls.API_URL.raw):
            return UsageError(f"Url must be inside the data-proxy ({cls.API_URL}. Got {url}")
        bucket_name_part_index = len(cls.API_URL.path.parts)
        if len(url.path.parts) <= bucket_name_part_index:
            return UsageError(f"Bad bucket url: {url}")
        token_result = ebrains_user_token or UserToken.get_global_login_token()
        if isinstance(token_result, UsageError):
            return token_result
        return BucketFs(
            bucket_name=url.path.parts[bucket_name_part_index],
            prefix=PurePosixPath("/".join(url.path.parts[bucket_name_part_index + 1:])),
            ebrains_user_token=token_result,
        )

    def _make_prefix(self, subpath: str) -> PurePosixPath:
        return self.prefix.joinpath(
            str(PurePosixPath("/").joinpath(subpath)).lstrip("/")
        )

    def _list_objects(self, *, prefix: str, limit: Optional[int] = None) -> List[Union[BucketObject, BucketSubdir]]:
        list_objects_path = self.bucket_url.updated_with(extra_search={
            "delimiter": "/",
            "prefix": prefix.lstrip("/"),
            "limit": str(limit or 50)
        })
        response = self.session.get(list_objects_path.raw)
        response.raise_for_status()
        payload_obj = ensureJsonObject(response.json())
        raw_objects = ensureJsonArray(payload_obj.get("objects"))

        items: List[Union[BucketObject, BucketSubdir]] = []
        for raw_obj in raw_objects:
            if "subdir" in ensureJsonObject(raw_obj):
                items.append(BucketSubdir.from_json_value(raw_obj))
            else:
                items.append(BucketObject.from_json_value(raw_obj))
        return items

    def _get_tmp_url(self, path: str) -> Url:
        object_url = self.url.concatpath(path)
        response = self.session.get(object_url.raw)
        response.raise_for_status()

        response_obj = ensureJsonObject(response.json())
        cscs_url = Url.parse(ensureJsonString(response_obj.get("url")))
        assert cscs_url is not None
        return cscs_url

    def getinfo(self, path: str, namespaces: Optional[Collection[str]] = ("basic",)) -> Info:
        cscs_url = self._get_tmp_url(path)
        head_response = self.cscs_session.head(cscs_url.raw)

        if head_response.status_code == 404:
            objects = self.listdir(path, limit=3)
            if len(objects) == 0:
                raise ResourceNotFound(path)
            is_dir = True
        else:
            is_dir = False

        return Info(
            raw_info={
                "basic": {
                    "name": PurePosixPath(path).name,
                    "is_dir": is_dir,
                },
                "details": {"type": ResourceType.directory if is_dir else ResourceType.file},
            }
        )

    def geturl(self, path: str, purpose: str = 'download') -> str:
        return self.url.concatpath(path).raw

    def listdir(self, path: str, limit: Optional[int] = None) -> List[str]:
        prefix = str(self._make_prefix(path))
        if not prefix.endswith("/"):
            prefix += "/"
        return [str(item.name) for item in self._list_objects(prefix=prefix, limit=limit)]

    def makedir(self, path: str, permissions: Optional[Permissions] = None, recreate: bool = False) -> SubFS[FS]:
        return BucketFs(
            bucket_name=self.bucket_name, prefix=self._make_prefix(path), ebrains_user_token=self.ebrains_user_token
        ) #type: ignore

    def makedirs(self, path: str, permissions: Optional[Permissions] = None, recreate: bool = False) -> SubFS[FS]:
        return self.makedir(path=path, permissions=permissions, recreate=recreate)

    def openbin(self, path: str, mode: str = "r", buffering: int = -1, **options: Dict[str, Any]) -> RemoteFile:
        def close_callback(f: RemoteFile):
            if mode == "r":
                return
            _ = f.seek(0)
            payload = f.read()
            url = self.url.concatpath(path).raw
            response = self.session.put(url)
            response.raise_for_status()
            response_obj = ensureJsonObject(response.json())
            url = ensureJsonString(response_obj.get("url"))
            response = self.cscs_session.put(url, data=payload)
            response.raise_for_status()

        contents = bytes()
        if mode in ("r", "r+", "w+", "a", "a+"):
            tile_url = self.url.concatpath(path).updated_with(extra_search={"redirect": "false"}).raw
            try:
                # t0 = time.time()
                data_proxy_response = self.session.get(tile_url)
                # t1 = time.time()
                data_proxy_response.raise_for_status()
                cscs_url = data_proxy_response.json()["url"]
                # t2 = time.time()
                cscs_response = self.cscs_session.get(cscs_url)
                # t3 = time.time()
                cscs_response.raise_for_status()
                # print(f"data-proxy time: \033[93m{t1 - t0}\033[0m  cscs time: \033[93m{t3 - t2}\033[0m  total: {t3 - t0}")
                contents = cscs_response.content
            except requests.HTTPError as e:
                print(f"~~~~~~>>>>>> something went wrong downloading load {tile_url}")
                if e.response.status_code == 404 and "r" in mode:
                    raise ResourceNotFound(path) from e
                raise e
        remote_file = RemoteFile(close_callback=close_callback, mode=mode, data=contents)
        if "a" in mode:
            _ = remote_file.seek(0, io.SEEK_END)
        return remote_file

    def remove(self, path: str) -> None:
        self.session.delete(self.url.concatpath(path).raw).raise_for_status()

    def removedir(self, path: str) -> None:
        raise NotImplementedError("Can't delete directories yet. Use the Data-Proxy GUI for now")
        return super().removedir(path)

    def setinfo(self, path: str, info) -> None:
        raise NotImplementedError
        return super().setinfo(path, info)

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "BucketFs":
        value_obj = ensureJsonObject(value)
        raw_token = value_obj.get("ebrains_user_token")
        if raw_token is not None:
            token = UserToken.from_json_value(raw_token)
        else:
            token_resut = UserToken.get_global_login_token()
            if isinstance(token_resut, UsageError):
                raise token_resut
            token = token_resut
        return BucketFs(
            bucket_name=ensureJsonString(value_obj.get("bucket_name")),
            prefix=PurePosixPath(ensureJsonString(value_obj.get("prefix"))),
            ebrains_user_token=token
        )

    def __setstate__(self, value_obj: Dict[str, Any]):
        raw_token = value_obj.get("ebrains_user_token")
        if raw_token is not None:
            token = UserToken.from_json_value(raw_token)
        else:
            token_resut = UserToken.get_global_login_token()
            if isinstance(token_resut, UsageError):
                raise token_resut
            token = token_resut

        self.__init__(
            bucket_name=ensureJsonString(value_obj.get("bucket_name")),
            prefix=PurePosixPath(ensureJsonString(value_obj.get("prefix"))),
            ebrains_user_token=token,
        )

    def to_json_value(self, omit_token: bool = False) -> JsonObject:
        out: Dict[str, JsonValue] = {
            "__class__": self.__class__.__name__,
            "bucket_name": self.bucket_name,
            "prefix": self.prefix.as_posix(),
        }
        if not omit_token:
            out["ebrains_user_token"] = self.ebrains_user_token.to_json_value()
        return out

    def __getstate__(self) -> JsonObject:
        return self.to_json_value()
