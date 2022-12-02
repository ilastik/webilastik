from typing import Any, Union, Mapping, Tuple, Protocol, List
import json
from collections.abc import Mapping

JsonLeafValue = Union[int, float, str, bool, None]

JsonObject = Mapping[str, "JsonValue"]

JsonArray = Tuple["JsonValue", ...] #tuples are invariant

JsonValue = Union[JsonLeafValue, JsonArray, JsonObject]

#//////////////////////////////

class IJsonable(Protocol):
    def to_json_value(self) -> JsonValue:
        ...

JsonableArray = Tuple["JsonableValue", ...]

JsonableMapping = Mapping[str, "JsonableValue"]

JsonableValue = Union[JsonValue, IJsonable, JsonableArray, JsonableMapping]

def convert_to_json_value(value: JsonableValue) -> JsonValue:
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    if isinstance(value, tuple):
        return tuple(convert_to_json_value(v) for v in value)
    if isinstance(value, Mapping):
        return {k: convert_to_json_value(v) for k, v in value.items()}
    return value.to_json_value()

class BadJsonException(Exception):
    def __init__(self, json_str: str) -> None:
        super().__init__(f"Bad json: {json_str}")

def parse_json(value: str) -> "JsonValue | BadJsonException":
    try:
        return json.loads(value)
    except Exception:
        return BadJsonException(value)
