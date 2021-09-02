
from fs.osfs import OSFS
from ndstructs.utils.json_serializable import JsonValue, JsonObject, ensureJsonObject, ensureJsonString

from webilastik.filesystem import JsonableFilesystem



class OsFs(OSFS, JsonableFilesystem):
    def to_json_value(self) -> JsonObject:
        return {
            "__class__": self.__class__.__name__,
            "path": self.desc(""),
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "OsFs":
        value_obj = ensureJsonObject(value)
        return OsFs(ensureJsonString(value_obj.get("path")))