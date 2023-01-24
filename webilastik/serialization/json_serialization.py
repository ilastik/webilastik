from typing import Any, Callable, TypeVar, Union, Mapping, Tuple, Protocol, List
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
    def __init__(self, json_str: "str | bytes") -> None:
        super().__init__(f"Bad json: {json_str}")

def parse_json(value: "str | bytes") -> "JsonValue | BadJsonException":
    try:
        return json.loads(value)
    except Exception:
        return BadJsonException(value)

T = TypeVar("T")
def parse_typed_json(*, raw_json: str, json_value_parser: Callable[[JsonValue], "T | Exception"]) -> "T | Exception":
    json_value_result = parse_json(raw_json)
    if isinstance(json_value_result, Exception):
        return json_value_result
    return json_value_parser(json_value_result)

def parse_typed_json_from_env_var(*, var_name: str, json_value_parser: Callable[[JsonValue], "T | Exception"]) -> "T | Exception":
    import os
    env_var_name = "WEBILASTIK_SESSION_ALLOCATOR_CONFIG_JSON"
    raw_json_str = os.environ.get(env_var_name)
    if raw_json_str is None:
        return Exception(f"{env_var_name} is not set")
    return parse_typed_json(raw_json=raw_json_str, json_value_parser=json_value_parser)

