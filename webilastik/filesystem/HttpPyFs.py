import re
from pathlib import Path
from urllib.parse import urlparse, urljoin
import io
from typing import Collection, Dict, Iterable, List, Any, Callable, Optional, Tuple
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

from .RemoteFile import RemoteFile


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class HttpPyFs(FS):
    def __init__(self, url: str):
        super().__init__()
        self.url = url
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Can only handle http procotols")
        clean_path = Path(parsed.path or "/").resolve().as_posix()
        self.parsed_url = parsed._replace(path=clean_path)
        self.root_path = Path(self.parsed_url.path)

    def __getstate__(self) -> Dict[str, Any]:
        return {"url": self.url}

    def __setstate__(self, data: Dict[str, Any]):
        self.__init__(url=data["url"])

    def desc(self, path: str) -> str:
        return self._make_full_path(path)

    def _make_full_path(self, path: str) -> str:
        rel_path = urlparse(path).path.lstrip("/")
        new_url = self.parsed_url._replace(
            path=self.root_path.joinpath(rel_path).resolve(strict=False).as_posix()
        )
        return new_url.geturl()

    def geturl(self, path: str, purpose: str = 'download') -> str:
        return self._make_full_path(path)

    def _delete_object(self, path: str) -> None:
        full_path = self._make_full_path(path)
        eprint(f"Removing object at {full_path}")
        resp = requests.delete(full_path)
        resp.raise_for_status()

    def _put_object(self, path: str, contents: bytes):
        full_path = self._make_full_path(path)
        resource_type = self._get_type(full_path)
        if resource_type == ResourceType.file:
            eprint(f"Overwriting object at {full_path}")
            self._delete_object(full_path)
        elif resource_type == ResourceType.directory:
            raise ValueError(f"{full_path} is a directory")
        assert full_path != "/"
        response = requests.put(full_path, data=contents, headers={"Content-Type": "application/octet-stream"})
        response.raise_for_status()

    def _get_object(self, path: str) -> Tuple[CaseInsensitiveDict, bytes]:
        full_path = self._make_full_path(path)
        response = requests.get(full_path)
        response.raise_for_status()
        return response.headers, response.content

    def _head_object(self, path: str) -> CaseInsensitiveDict:
        full_path = self._make_full_path(path)
        resp = requests.head(full_path)
        resp.raise_for_status()
        return resp.headers

    def _get_type(self, path: str) -> ResourceType:
        full_path = self._make_full_path(path)
        headers = self._head_object(path)
        if headers["Content-Type"] == "application/octet-stream":
            return ResourceType.file
        return ResourceType.directory

    def getinfo(self, path: str, namespaces: Optional[Collection[str]] = ("basic",)) -> Info:
        full_path = self._make_full_path(path)
        resource_type = self._get_type(full_path)
        return Info(
            raw_info={
                "basic": {
                    "name": Path(full_path).name,
                    "is_dir": True if resource_type == ResourceType.directory else False,
                },
                "details": {"type": resource_type},
            }
        )

    def openbin(self, path: str, mode: str = "r", buffering: int = -1, **options: Dict[str, Any]) -> RemoteFile:
        def close_callback(f: RemoteFile):
            if mode != "r":
                f.seek(0)
                self._put_object(path, f.read())

        try:
            meta, contents = self._get_object(path)
            remote_file = RemoteFile(close_callback=close_callback, mode=mode, data=contents)
            if mode.startswith("a"):
                remote_file.seek(0, io.SEEK_END)
            return remote_file
        except HTTPError as e:
            if e.response.status_code == 404:
                if mode in ("r", "r+"):
                    raise ResourceNotFound(path) from e
                return RemoteFile(close_callback=close_callback, mode=mode, data=bytes())
            raise e

    def opendir(self, path: str, factory=None) -> SubFS["HttpPyFs"]:
        return HttpPyFs(self._make_full_path(path))

    def listdir(self, path: str) -> List[str]:
        raise NotImplementedError("Can't reliably list directories via http")

    def makedir(
        self, path: str, permissions: Optional[Permissions] = None, recreate: bool = False
    ) -> SubFS["HttpPyFs"]:
        raise NotImplementedError("Can't reliably create directories via http")

    def remove(self, path: str) -> None:
        self._delete_object(path)

    def removedir(self, path: str) -> None:
        raise NotImplementedError("removedir")

    def setinfo(self, path, info):
        raise NotImplementedError("setinfo")
