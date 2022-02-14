# pyright: reportUnusedImport=false
from typing import Callable, TypeVar

from ndstructs.utils.json_serializable import JsonObject, JsonValue
from .flatten import flatten, unflatten, listify
import datetime

def get_now_string() -> str:
    now = datetime.datetime.now()
    return f"{now.year:02}y{now.month:02}m{now.day:02}d__{now.hour:02}h{now.minute:02}m{now.second:02}s"

T = TypeVar("T")

class Absent:
    pass

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Absent)

    @staticmethod
    def coalesce(value: "T | Absent", default: T) -> T:
        return default if isinstance(value, Absent) else value

    @staticmethod
    def tryGetFromObject(key: str, json_object: JsonObject, parser: Callable[[JsonValue], T]) -> "T | None | Absent":
        if key in json_object:
            value = json_object[key]
            if value is None:
                return value
            return parser(json_object[key])
        return Absent()