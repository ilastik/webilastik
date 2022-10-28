from abc import abstractmethod
import json
from typing import Sequence

from ndstructs.utils.json_serializable import IJsonable, JsonValue, ensureJsonObject, ensureJsonString
from fs.base import FS
from webilastik.ui.usage_error import UsageError

from webilastik.utility.url import Protocol, Url




class JsonableFilesystem(FS, IJsonable):
    @classmethod
    @abstractmethod
    def from_json_value(cls, value: JsonValue) -> "JsonableFilesystem":
        from .http_fs import HttpFs, SwiftTempUrlFs
        from .osfs import OsFs
        from .bucket_fs import BucketFs

        # FIXME: Maybe register these via __init_subclass__?
        value_obj = ensureJsonObject(value)
        fs_class_name = ensureJsonString(value_obj.get("__class__"))
        if fs_class_name == HttpFs.__name__:
            return HttpFs.from_json_value(value)
        if fs_class_name == SwiftTempUrlFs.__name__:
            return SwiftTempUrlFs.from_json_value(value)
        if fs_class_name == OsFs.__name__:
            return OsFs.from_json_value(value)
        if fs_class_name == BucketFs.__name__:
            return BucketFs.from_json_value(value)

        raise ValueError(f"Could not deserialize filesystem from:\n{json.dumps(value, indent=4)}")

    @abstractmethod
    def to_json_value(self) -> JsonValue:
        pass

    @staticmethod
    def from_url(url: Url) -> "JsonableFilesystem | Exception":
        from webilastik.filesystem.osfs import OsFs
        from webilastik.filesystem.bucket_fs import BucketFs
        from webilastik.filesystem.http_fs import HttpFs

        if url.protocol == "file":
            return OsFs(url.path.as_posix())
        if url.raw.startswith(BucketFs.API_URL.raw):
            return BucketFs.try_from_url(url=url)
        return HttpFs.try_from_url(url)
