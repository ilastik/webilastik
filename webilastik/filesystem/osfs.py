
from fs.osfs import OSFS
from ndstructs.utils.json_serializable import JsonValue, JsonObject, ensureJsonObject, ensureJsonString

from webilastik.filesystem import JsonableFilesystem
from webilastik.server.message_schema import OsfsMessage



class OsFs(OSFS, JsonableFilesystem):
    def to_json_value(self) -> JsonObject:
        return {
            "__class__": self.__class__.__name__,
            "path": self.desc(""),
        }

    def __getstate__(self) -> JsonObject:
        return self.to_json_value()

    def to_message(self) -> "OsfsMessage":
        return OsfsMessage(path=self.root_path)

    @classmethod
    def from_message(cls, message: OsfsMessage) -> "OsFs":
        return OsFs(message.path)

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "OsFs":
        value_obj = ensureJsonObject(value)
        return OsFs(ensureJsonString(value_obj.get("path")))

    def __setstate__(self, value: JsonObject):
        self.__init__(
            ensureJsonString(value.get("path"))
        )