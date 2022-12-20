from typing import Dict, Literal, Optional, Mapping, Final, Tuple
from pathlib import PurePosixPath

import requests

from webilastik.filesystem import IFilesystem, FsIoException, FsFileNotFoundException, FsDirectoryContents
from webilastik.utility.url import Url
from webilastik.server.rpc.dto import HttpFsDto
from webilastik.utility.request import ErrRequestCompletedAsFailure, ErrRequestCrashed, request as safe_request

_sessions: Dict[str, requests.Session] = {}

def _do_request(
    method: Literal["get", "put", "post", "delete"],
    url: Url,
    data: Optional[bytes] = None,
    headers: "Mapping[str, str] | None" = None,
) -> "bytes | ErrRequestCompletedAsFailure | ErrRequestCrashed":
    session = _sessions.get(url.hostname)
    if session is None:
        session = requests.Session()
        _sessions[url.hostname] = session
    return safe_request(session=session, method=method, url=url, data=data, headers=headers)


class HttpFs(IFilesystem):
    def __init__(
        self,
        *,
        protocol: Literal["http", "https"],
        hostname: str,
        path: PurePosixPath,
        port: Optional[int] = None,
        search: Optional[Mapping[str, str]] = None,
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
        result = _do_request(
            method="post",
            url=self.base.concatpath(path),
            data=contents,
        )
        if isinstance(result, Exception):
            return FsIoException(result)

    def create_directory(self, path: PurePosixPath) -> "None | FsIoException":
        return None

    def read_file(self, path: PurePosixPath) -> "bytes | FsIoException | FsFileNotFoundException":
        result = _do_request(
            method="get",
            url=self.base.concatpath(path),
        )
        if isinstance(result, bytes):
            return result
        if isinstance(result, ErrRequestCompletedAsFailure) and result.response.status_code == 404:
            return FsFileNotFoundException(path=path)
        return FsIoException(result)

    def delete(self, path: PurePosixPath) -> "None | FsIoException":
        result = _do_request(method="delete", url=self.base.concatpath(path))
        if isinstance(result, Exception):
            return FsIoException(result)

    def geturl(self, path: PurePosixPath) -> Url:
        return self.base.concatpath(path)
