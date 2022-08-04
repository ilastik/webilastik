import uuid
from dataclasses import dataclass

from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString

@dataclass
class UserInfo:
    sub: uuid.UUID
    preferred_username: str

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "UserInfo":
        value_obj = ensureJsonObject(value)
        return UserInfo(
            sub=uuid.UUID(ensureJsonString(value_obj["sub"])),
            preferred_username=ensureJsonString(value_obj["preferred_username"]),
        )
