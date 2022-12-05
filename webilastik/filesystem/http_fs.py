from typing import Literal, Optional, Mapping, Final, Tuple
from pathlib import PurePosixPath

import requests

from webilastik.filesystem import IFilesystem, FsIoException, FsFileNotFoundException, FsDirectoryContents
from webilastik.utility.url import Url
from webilastik.server.rpc.dto import HttpFsDto

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
