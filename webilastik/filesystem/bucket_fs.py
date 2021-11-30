from pathlib import PurePosixPath
import io
from typing import Any, Collection, Optional, Union, Dict, List
from datetime import datetime

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
from webilastik.utility.url import Url


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
    API_URL = Url.parse("https://data-proxy.ebrains.eu/api/buckets")

    def __init__(self, bucket_name: str, prefix: PurePosixPath, ebrains_user_token: UserToken):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.ebrains_user_token = ebrains_user_token
        self.bucket_url = self.API_URL.concatpath(bucket_name)
        self.url = self.bucket_url.concatpath(prefix)
        super().__init__()

        self.session = requests.Session()
        self.session.headers.update(ebrains_user_token.as_auth_header())
        self.write_session = requests.Session()

    @classmethod
    def try_from_url(cls, url: Url, ebrains_user_token: UserToken) -> Optional["BucketFs"]:
        if not url.raw.startswith(cls.API_URL.raw):
            return None
        bucket_name_part_index = len(cls.API_URL.path.parts)
        if len(url.path.parts) <= bucket_name_part_index:
            return None
        return BucketFs(
            bucket_name=url.path.parts[bucket_name_part_index],
            prefix=PurePosixPath("/".join(url.path.parts[bucket_name_part_index + 1:])),
            ebrains_user_token=ebrains_user_token,
        )

    def _make_prefix(self, subpath: str) -> PurePosixPath:
        return self.prefix.joinpath(
            str(PurePosixPath("/").joinpath(subpath)).lstrip("/")
        )

    def _list_objects(self, *, prefix: str, limit: int = 50) -> List[Union[BucketObject, BucketSubdir]]:
        list_objects_path = self.bucket_url.updated_with(extra_search={
            "delimiter": "/",
            "prefix": prefix.lstrip("/"),
            "limit": str(limit)
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

    def _get_tmp_url(self, path: str) -> Optional[Url]:
        object_url = self.url.concatpath(path)
        response = self.session.get(object_url.raw)

        if response.status_code == 200:
            response_obj = ensureJsonObject(response.json())
            return Url.parse(ensureJsonString(response_obj.get("url")))
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return None # FIXME?

    def getinfo(self, path: str, namespaces: Optional[Collection[str]] = ("basic",)) -> Info:
        if self._get_tmp_url(path) != None:
            is_dir = False
        else:
            sub_items = self.listdir(path)
            if len(sub_items) == 0:
                raise ResourceNotFound(path)
            else:
                is_dir = True

        return Info(
            raw_info={
                "basic": {
                    "name": PurePosixPath(path).name,
                    "is_dir": is_dir,
                },
                "details": {"type": ResourceType.directory if is_dir else ResourceType.file},
            }
        )

    def listdir(self, path: str) -> List[str]:
        prefix = str(self._make_prefix(path))
        if not prefix.endswith("/"):
            prefix += "/"
        return [str(item.name) for item in self._list_objects(prefix=prefix)]

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
            response = self.write_session.put(url, data=payload)
            response.raise_for_status()

        contents = bytes()
        if mode in ("r", "r+", "w+", "a", "a+"):
            try:
                response = self.session.get(self.url.concatpath(path).updated_with(extra_search={"redirect": "true"}).raw)
                response.raise_for_status()
                contents = response.content
            except requests.HTTPError as e:
                if e.response.status_code == 404 and "r" in mode:
                    raise ResourceNotFound(path) from e
        remote_file = RemoteFile(close_callback=close_callback, mode=mode, data=contents)
        if "a" in mode:
            _ = remote_file.seek(0, io.SEEK_END)
        return remote_file

    def remove(self, path: str) -> None:
        self.session.delete(self.url.concatpath(path).raw).raise_for_status()

    def removedir(self, path: str) -> None:
        raise NotImplemented
        return super().removedir(path)

    def setinfo(self, path: str, info) -> None:
        raise NotImplemented
        return super().setinfo(path, info)

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "BucketFs":
        value_obj = ensureJsonObject(value)
        return BucketFs(
            bucket_name=ensureJsonString(value_obj.get("bucket_name")),
            prefix=PurePosixPath(ensureJsonString(value_obj.get("prefix"))),
            ebrains_user_token=UserToken.from_json_value(value_obj.get("ebrains_user_token"))
        )

    def __setstate__(self, value_obj: Dict[str, Any]):
        self.__init__(
            bucket_name=ensureJsonString(value_obj.get("bucket_name")),
            prefix=PurePosixPath(ensureJsonString(value_obj.get("prefix"))),
            ebrains_user_token=UserToken.from_json_value(value_obj.get("ebrains_user_token"))
        )

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": self.__class__.__name__,
            "bucket_name": self.bucket_name,
            "prefix": self.prefix.as_posix(),
            "ebrains_user_token": self.ebrains_user_token.to_json_value(),
        }

    def __getstate__(self) -> JsonObject:
        return self.to_json_value()
