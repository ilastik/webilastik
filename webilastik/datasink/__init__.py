from abc import ABC, abstractmethod
import json
from typing import Callable, Dict, Optional
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString

import numpy as np

from ndstructs import Shape5D, Interval5D, Array5D
from webilastik.utility.url import Url

DATASINK_FROM_JSON_CONSTRUCTORS: Dict[str, Callable[[JsonValue], "DataSink"]] = {}

class DataSink(ABC):
    def __init__(
        self,
        *,
        tile_shape: Shape5D,
        interval: Interval5D,
        dtype: np.dtype, #type: ignore
        url: Optional[Url] = None
    ):
        self.tile_shape = tile_shape
        self.interval = interval
        self.dtype = dtype # type: ignore
        self.url = url

        self.shape = self.interval.shape
        self.location = interval.start

    @abstractmethod
    def write(self, data: Array5D) -> None:
        pass

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": self.__class__.__name__,
            "tile_shape": self.tile_shape.to_json_value(),
            "interval": self.interval.to_json_value(),
            "dtype": str(self.dtype.name), #type: ignore
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "DataSink":
        value_obj = ensureJsonObject(value)
        class_name = ensureJsonString(value_obj.get("__class__"))
        if class_name not in DATASINK_FROM_JSON_CONSTRUCTORS:
            raise ValueError(f"Could not deserialize DataSink from {json.dumps(value)}")
        return DATASINK_FROM_JSON_CONSTRUCTORS[class_name](value)