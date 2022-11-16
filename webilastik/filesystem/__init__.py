from abc import abstractmethod
import json

from ndstructs.utils.json_serializable import IJsonable, JsonValue, ensureJsonObject, ensureJsonString
from fs.base import FS
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
            return HttpFs.from_message(message)
        if isinstance(message, OsfsDto):
            return OsFs.from_message(message)
        if isinstance(message, BucketFSDto):
            return BucketFs.from_message(message)

    @abstractmethod
    def to_message(self) -> "OsfsDto | HttpFsDto | BucketFSDto":
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
