import json
import os
from pathlib import Path
import io
from typing import Collection, Dict, List, Any, Mapping, Optional, Tuple, Union
import requests
from requests import HTTPError
import sys

from fs.base import FS
from fs.subfs import SubFS
from fs.info import Info
from fs.errors import DirectoryExpected, FileExpected, ResourceNotFound
from fs.permissions import Permissions
from fs.enums import ResourceType
from requests.models import CaseInsensitiveDict
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString
from webilastik.ui.usage_error import UsageError

from .RemoteFile import RemoteFile
from webilastik.filesystem import JsonableFilesystem
from webilastik.utility.url import Url, Protocol


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class HttpFs(JsonableFilesystem):
    def __init__(self, read_url: Url, write_url: Optional[Url] = None, headers: Optional[Mapping[str, str]] = None):
        super().__init__()
        self.read_url = read_url
        self.write_url = write_url or read_url

        if not set([self.read_url.protocol, self.write_url.protocol]).issubset([Protocol.HTTP, Protocol.HTTPS]):
            raise ValueError("Can only handle http procotols")
        self.requests_verify: Union[str, bool] = os.environ.get("CA_CERT_PATH", True)
        if isinstance(self.requests_verify, str) and not Path(self.requests_verify).exists():
            raise ValueError(f"CA_CERT_PATH '{self.requests_verify}' not found")

        self.headers = headers or {}
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    @classmethod
    def try_from_url(cls, url: Url) -> "HttpFs | UsageError":
        if url.protocol not in (Protocol.HTTP, Protocol.HTTPS):
            return UsageError(f"Bad url for HttpFs: {url}")
        return HttpFs(read_url=url)

    def to_json_value(self) -> JsonObject:
        return {
            "read_url": self.read_url.raw,
            "write_url": self.write_url.raw,
            "__class__": self.__class__.__name__,
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "HttpFs":
        value_obj = ensureJsonObject(value)

        raw_headers = value_obj.get("headers")
        if raw_headers is None:
            headers = {}
        else:
            headers_obj = ensureJsonObject(raw_headers)
            headers = {ensureJsonString(k): ensureJsonString(v) for k,v in headers_obj.items()}

        read_url = Url.parse(ensureJsonString(value_obj.get("read_url")))
        if read_url is None:
            raise ValueError(f"Bad 'read_url' in json payload: {json.dumps(value, indent=4)}")

        raw_write_url = value_obj.get("write_url")
        if raw_write_url is None:
            write_url = None
        else:
            write_url = Url.parse(ensureJsonString(raw_write_url))
            if write_url is None:
                raise ValueError(f"Bad write_url in HttpFs payload: {json.dumps(value, indent=4)}")

        return cls(
            read_url=read_url,
            write_url=write_url,
            headers=headers,
        )

    def __getstate__(self) -> JsonObject:
        return self.to_json_value()

    def __setstate__(self, data: Dict[str, Any]):
        url = HttpFs.from_json_value(data)
        self.__init__(
            read_url=url.read_url,
            write_url=url.write_url,
            headers=url.headers,
        )

    def desc(self, path: str) -> str:
        return self.read_url.concatpath(path).raw

    def geturl(self, path: str, purpose: str = 'download') -> str:
        return self.read_url.concatpath(path).raw

    def _delete_object(self, subpath: str) -> None:
        full_path = self.write_url.concatpath(subpath)
        eprint(f"Removing object at {full_path}")
        resp = self.session.delete(full_path.raw, verify=self.requests_verify)
        resp.raise_for_status()

    def _put_object(self, subpath: str, contents: bytes) -> requests.Response:
        full_path = self.write_url.concatpath(subpath)
        assert full_path.raw != "/"

        # try:
        #     resource_type = self._get_type(subpath)
        #     if resource_type == ResourceType.directory:
        #         raise ValueError(f"{full_path} is a directory")
        #     eprint(f"Overwriting object at {full_path}")
        #     self._delete_object(full_path.raw)
        # except HTTPError as e:
        #     if e.response.status_code == 404:
        #         pass

        response = self.session.put(
            full_path.raw, data=contents, headers={"Content-Type": "application/octet-stream"}, verify=self.requests_verify
        )
        response.raise_for_status()
        return response

    def _get_object(self, subpath: str) -> Tuple["CaseInsensitiveDict[str]", bytes]:
        full_path = self.read_url.concatpath(subpath)
        response = self.session.get(full_path.raw, verify=self.requests_verify)
        response.raise_for_status()
        return response.headers, response.content

    def _head_object(self, subpath: str) -> "CaseInsensitiveDict[str]":
        full_path = self.read_url.concatpath(subpath)
        resp = self.session.head(full_path.raw, verify=self.requests_verify)
        if resp.status_code == 404:
            raise ResourceNotFound(subpath)
        else:
            resp.raise_for_status()
        return resp.headers

    def _get_type(self, subpath: str) -> ResourceType:
        headers = self._head_object(subpath)
        if headers["Content-Type"] == "application/octet-stream":
            return ResourceType.file
        return ResourceType.directory

    def getinfo(self, path: str, namespaces: Optional[Collection[str]] = ("basic",)) -> Info:
        full_path = self.read_url.concatpath(path)
        resource_type = self._get_type(path)
        return Info(
            raw_info={
                "basic": {
                    "name": full_path.path.name,
                    "is_dir": True if resource_type == ResourceType.directory else False,
                },
                "details": {"type": resource_type},
            }
        )

    def openbin(self, path: str, mode: str = "r", buffering: int = -1, **options: Dict[str, Any]) -> RemoteFile:
        def close_callback(f: RemoteFile):
            if mode == "r":
                return
            _ = f.seek(0)
            self._put_object(path, f.read()).raise_for_status()

        contents = bytes()
        if mode in ("r", "r+", "w+", "a", "a+"):
            try:
                _, contents = self._get_object(path)
            except HTTPError as e:
                if e.response.status_code == 404 and "r" in mode:
                    raise ResourceNotFound(path) from e
        remote_file = RemoteFile(close_callback=close_callback, mode=mode, data=contents)
        if "a" in mode:
            _ = remote_file.seek(0, io.SEEK_END)
        return remote_file

    def opendir(self, path: str, factory=None) -> SubFS[FS]:
        #FIXME: is the typing correct?
        return HttpFs(self.read_url.concatpath(path)) #type: ignore

    def listdir(self, path: str) -> List[str]:
        raise NotImplementedError("Can't reliably list directories via http")

    def makedir(
        self, path: str, permissions: Optional[Permissions] = None, recreate: bool = False
    ) -> SubFS[FS]:
        raise NotImplementedError("makedir")

    def remove(self, path: str) -> None:
        self._delete_object(path)

    def removedir(self, path: str) -> None:
        raise NotImplementedError("removedir")

    def setinfo(self, path, info):
        raise NotImplementedError("setinfo")

class SwiftTempUrlFs(HttpFs):
    def exists(self, path: str) -> bool:
        # FIXME: folders with never exist
        try:
            _ = self._get_object(path)
            return True
        except HTTPError as e:
            if e.response.status_code == 404:
                return False
            raise

    def makedir(self, path: str, permissions: Optional[Permissions] = None, recreate: bool = False) -> SubFS[FS]:
        return self.opendir(path)

    def makedirs(self, path: str, permissions: Optional[Permissions]=None, recreate: bool = True) -> SubFS[FS]:
        return self.opendir(path)