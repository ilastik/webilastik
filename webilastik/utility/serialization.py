from typing import Any, Union, Sequence, Mapping, Optional, List, Generic, TypeVar, Type
from typing_extensions import Protocol
from collections.abc import Mapping as MappingCollection



JSON_LEAF_VALUE = Union[str, int, float, bool, None]
JSON_ARRAY = Sequence["JSON_VALUE"]
JSON_OBJECT = Mapping[str, "JSON_VALUE"]
JSON_VALUE = Union[JSON_LEAF_VALUE, JSON_ARRAY, JSON_OBJECT]

def _get_value(*, key: str, data: JSON_VALUE, value_class: type) -> Any:
    if not isinstance(data, MappingCollection):
            raise TypeError(f"Expected data to be a JSON object, found this: {data}")
    value = data[key]
    if isinstance(value, int) and value_class == float:
        value = float(value)
    if not isinstance(value, value_class):
        raise TypeError(f"Expected {key} to be a {value_class.__name__}, but found this: {value}")
    return value


T = TypeVar("T", bound=JSON_VALUE)
class ValueGetter(Generic[T]):
    """A utility to safely retrieve values from Json objects. Must be a class in order to be generic"""
    def __init__(self, value_class: Type[T]):
        self.value_class = value_class

    def get(self, *, key: str, data: JSON_VALUE) -> T:
        return _get_value(key=key, data=data, value_class=self.value_class)

    def get_optional(self, *, key: str, data: JSON_VALUE) -> Optional[T]:
        try:
            return self.get(key=key, data=data)
        except KeyError:
            return None

    def get_default(self, *, key: str, data: JSON_VALUE, default: T) -> T:
        value = self.get_optional(key=key, data=data)
        return value if value != None else default

    def ensure_class(self, *, data: JSON_VALUE):
        if ValueGetter(str).get(key="__class__", data=data) != self.value_class.__name__:
            raise TypeError(f"Expected data to be of __class__ {self.value_class.__name__}. Found this: {data}")

    @classmethod
    def get_class_name(cls, *, data: JSON_VALUE) -> str:
        return ValueGetter(str).get(key="__class__", data=data)


class ListGetter(Generic[T]):
    def __init__(self, element_class: Type[T]):
        self.element_class = element_class

    def get(self, *, key: str, data: JSON_VALUE) -> List[T]:
        values = _get_value(key=key, data=data, value_class=list)
        if not all(isinstance(v, self.element_class) for v in values):
            raise TypeError(f"Expected {key} to be a list of {self.element_class.__name__}, but found this: {values}")
        return values

    @classmethod
    def get_list_of_objects(cls, *, key: str, data: JSON_VALUE) -> List[JSON_OBJECT]:
        objects =  _get_value(key=key, data=data, value_class=list)
        if not all(isinstance(obj, MappingCollection) for obj in objects):
            raise TypeError(f"Expected all items of {key} to be objects, but found this: {data}")
        return objects

class ObjectGetter:
    @classmethod
    def get(cls, key: str, data: JSON_VALUE) -> JSON_OBJECT:
        return _get_value(key=key, data=data, value_class=MappingCollection)
    @classmethod
    def get_optional(cls, key: str, data: JSON_VALUE) -> Optional[JSON_OBJECT]:
        try:
            return cls.get(key=key, data=data)
        except KeyError:
            return None
