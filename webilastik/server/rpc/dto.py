# pyright: strict

# Automatically generated via /home/builder/source/webilastik/webilastik/server/rpc/__main__.py.
# Edit the template file instead of this one!

import json
from typing import List, Dict

from ndstructs.point5D import Point5D, Shape5D, Interval5D

from webilastik.serialization.json_serialization import (
    JsonObject,
    JsonValue,
    convert_to_json_value,
)
from webilastik.server.rpc import DataTransferObject, MessageParsingError

from typing import Literal, Optional, Tuple, Union, Mapping, Any, cast

from dataclasses import dataclass

from ndstructs.point5D import Interval5D, Point5D, Shape5D

import numpy as np

from webilastik.server.rpc import DataTransferObject


def parse_as_int(value: JsonValue) -> "int | MessageParsingError":
    if isinstance(value, int):
        return value

    return MessageParsingError(f"Could not parse {json.dumps(value)} as int")


def parse_as_ColorDto(value: JsonValue) -> "ColorDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(f"Could not parse {json.dumps(value)} as ColorDto")
    if value.get("__class__") != "ColorDto":
        return MessageParsingError(f"Could not parse {json.dumps(value)} as ColorDto")
    tmp_r = parse_as_int(value.get("r"))
    if isinstance(tmp_r, MessageParsingError):
        return tmp_r
    tmp_g = parse_as_int(value.get("g"))
    if isinstance(tmp_g, MessageParsingError):
        return tmp_g
    tmp_b = parse_as_int(value.get("b"))
    if isinstance(tmp_b, MessageParsingError):
        return tmp_b
    return ColorDto(
        r=tmp_r,
        g=tmp_g,
        b=tmp_b,
    )


@dataclass
class ColorDto(DataTransferObject):
    r: int
    g: int
    b: int

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "ColorDto",
            "r": self.r,
            "g": self.g,
            "b": self.b,
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "ColorDto | MessageParsingError":
        return parse_as_ColorDto(value)


def parse_as_str(value: JsonValue) -> "str | MessageParsingError":
    if isinstance(value, str):
        return value

    return MessageParsingError(f"Could not parse {json.dumps(value)} as str")


def parse_as_LabelHeaderDto(value: JsonValue) -> "LabelHeaderDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as LabelHeaderDto"
        )
    if value.get("__class__") != "LabelHeaderDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as LabelHeaderDto"
        )
    tmp_name = parse_as_str(value.get("name"))
    if isinstance(tmp_name, MessageParsingError):
        return tmp_name
    tmp_color = parse_as_ColorDto(value.get("color"))
    if isinstance(tmp_color, MessageParsingError):
        return tmp_color
    return LabelHeaderDto(
        name=tmp_name,
        color=tmp_color,
    )


@dataclass
class LabelHeaderDto(DataTransferObject):
    name: str
    color: ColorDto

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "LabelHeaderDto",
            "name": self.name,
            "color": self.color.to_json_value(),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "LabelHeaderDto | MessageParsingError":
        return parse_as_LabelHeaderDto(value)


Protocol = Literal["http", "https", "file", "memory"]


def parse_as_Literal_of__quote_precomputed_quote__endof_(
    value: JsonValue,
) -> "Literal['precomputed'] | MessageParsingError":
    tmp_0 = parse_as_str(value)
    if not isinstance(tmp_0, MessageParsingError) and tmp_0 == "precomputed":
        return tmp_0
    return MessageParsingError(f"Could not parse {value} as Literal['precomputed']")


def parse_as_None(value: JsonValue) -> "None | MessageParsingError":
    if isinstance(value, type(None)):
        return value

    return MessageParsingError(f"Could not parse {json.dumps(value)} as None")


def parse_as_Union_of_Literal_of__quote_precomputed_quote__endof_0None_endof_(
    value: JsonValue,
) -> "Union[Literal['precomputed'], None] | MessageParsingError":
    parsed_option_0 = parse_as_Literal_of__quote_precomputed_quote__endof_(value)
    if not isinstance(parsed_option_0, MessageParsingError):
        return parsed_option_0
    parsed_option_1 = parse_as_None(value)
    if not isinstance(parsed_option_1, MessageParsingError):
        return parsed_option_1
    return MessageParsingError(
        f"Could not parse {json.dumps(value)} into Union[Literal['precomputed'], None]"
    )


def parse_as_Literal_of__quote_http_quote_0_quote_https_quote_0_quote_file_quote_0_quote_memory_quote__endof_(
    value: JsonValue,
) -> "Literal['http', 'https', 'file', 'memory'] | MessageParsingError":
    tmp_0 = parse_as_str(value)
    if not isinstance(tmp_0, MessageParsingError) and tmp_0 == "http":
        return tmp_0
    tmp_1 = parse_as_str(value)
    if not isinstance(tmp_1, MessageParsingError) and tmp_1 == "https":
        return tmp_1
    tmp_2 = parse_as_str(value)
    if not isinstance(tmp_2, MessageParsingError) and tmp_2 == "file":
        return tmp_2
    tmp_3 = parse_as_str(value)
    if not isinstance(tmp_3, MessageParsingError) and tmp_3 == "memory":
        return tmp_3
    return MessageParsingError(
        f"Could not parse {value} as Literal['http', 'https', 'file', 'memory']"
    )


def parse_as_Union_of_int0None_endof_(
    value: JsonValue,
) -> "Union[int, None] | MessageParsingError":
    parsed_option_0 = parse_as_int(value)
    if not isinstance(parsed_option_0, MessageParsingError):
        return parsed_option_0
    parsed_option_1 = parse_as_None(value)
    if not isinstance(parsed_option_1, MessageParsingError):
        return parsed_option_1
    return MessageParsingError(
        f"Could not parse {json.dumps(value)} into Union[int, None]"
    )


def parse_as_Mapping_of_str0str_endof_(
    value: JsonValue,
) -> "Mapping[str, str] | MessageParsingError":
    from collections.abc import Mapping as AbcMapping

    if not isinstance(value, AbcMapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as a Mapping[str, str]"
        )
    out: Dict[str, str] = {}
    for key, val in value.items():
        parsed_key = parse_as_str(key)
        if isinstance(parsed_key, MessageParsingError):
            return parsed_key
        parsed_val = parse_as_str(val)
        if isinstance(parsed_val, MessageParsingError):
            return parsed_val
        out[parsed_key] = parsed_val
    return out


def parse_as_Union_of_Mapping_of_str0str_endof_0None_endof_(
    value: JsonValue,
) -> "Union[Mapping[str, str], None] | MessageParsingError":
    parsed_option_0 = parse_as_Mapping_of_str0str_endof_(value)
    if not isinstance(parsed_option_0, MessageParsingError):
        return parsed_option_0
    parsed_option_1 = parse_as_None(value)
    if not isinstance(parsed_option_1, MessageParsingError):
        return parsed_option_1
    return MessageParsingError(
        f"Could not parse {json.dumps(value)} into Union[Mapping[str, str], None]"
    )


def parse_as_Union_of_str0None_endof_(
    value: JsonValue,
) -> "Union[str, None] | MessageParsingError":
    parsed_option_0 = parse_as_str(value)
    if not isinstance(parsed_option_0, MessageParsingError):
        return parsed_option_0
    parsed_option_1 = parse_as_None(value)
    if not isinstance(parsed_option_1, MessageParsingError):
        return parsed_option_1
    return MessageParsingError(
        f"Could not parse {json.dumps(value)} into Union[str, None]"
    )


def parse_as_UrlDto(value: JsonValue) -> "UrlDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(f"Could not parse {json.dumps(value)} as UrlDto")
    if value.get("__class__") != "UrlDto":
        return MessageParsingError(f"Could not parse {json.dumps(value)} as UrlDto")
    tmp_datascheme = (
        parse_as_Union_of_Literal_of__quote_precomputed_quote__endof_0None_endof_(
            value.get("datascheme")
        )
    )
    if isinstance(tmp_datascheme, MessageParsingError):
        return tmp_datascheme
    tmp_protocol = parse_as_Literal_of__quote_http_quote_0_quote_https_quote_0_quote_file_quote_0_quote_memory_quote__endof_(
        value.get("protocol")
    )
    if isinstance(tmp_protocol, MessageParsingError):
        return tmp_protocol
    tmp_hostname = parse_as_str(value.get("hostname"))
    if isinstance(tmp_hostname, MessageParsingError):
        return tmp_hostname
    tmp_port = parse_as_Union_of_int0None_endof_(value.get("port"))
    if isinstance(tmp_port, MessageParsingError):
        return tmp_port
    tmp_path = parse_as_str(value.get("path"))
    if isinstance(tmp_path, MessageParsingError):
        return tmp_path
    tmp_search = parse_as_Union_of_Mapping_of_str0str_endof_0None_endof_(
        value.get("search")
    )
    if isinstance(tmp_search, MessageParsingError):
        return tmp_search
    tmp_fragment = parse_as_Union_of_str0None_endof_(value.get("fragment"))
    if isinstance(tmp_fragment, MessageParsingError):
        return tmp_fragment
    return UrlDto(
        datascheme=tmp_datascheme,
        protocol=tmp_protocol,
        hostname=tmp_hostname,
        port=tmp_port,
        path=tmp_path,
        search=tmp_search,
        fragment=tmp_fragment,
    )


@dataclass
class UrlDto(DataTransferObject):
    datascheme: Optional[Literal["precomputed"]]
    protocol: Literal["http", "https", "file", "memory"]
    hostname: str
    port: Optional[int]
    path: str
    search: Optional[Mapping[str, str]]
    fragment: Optional[str]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "UrlDto",
            "datascheme": convert_to_json_value(self.datascheme),
            "protocol": self.protocol,
            "hostname": self.hostname,
            "port": convert_to_json_value(self.port),
            "path": self.path,
            "search": convert_to_json_value(self.search),
            "fragment": convert_to_json_value(self.fragment),
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "UrlDto | MessageParsingError":
        return parse_as_UrlDto(value)


def parse_as_Point5DDto(value: JsonValue) -> "Point5DDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(f"Could not parse {json.dumps(value)} as Point5DDto")
    if value.get("__class__") != "Point5DDto":
        return MessageParsingError(f"Could not parse {json.dumps(value)} as Point5DDto")
    tmp_x = parse_as_int(value.get("x"))
    if isinstance(tmp_x, MessageParsingError):
        return tmp_x
    tmp_y = parse_as_int(value.get("y"))
    if isinstance(tmp_y, MessageParsingError):
        return tmp_y
    tmp_z = parse_as_int(value.get("z"))
    if isinstance(tmp_z, MessageParsingError):
        return tmp_z
    tmp_t = parse_as_int(value.get("t"))
    if isinstance(tmp_t, MessageParsingError):
        return tmp_t
    tmp_c = parse_as_int(value.get("c"))
    if isinstance(tmp_c, MessageParsingError):
        return tmp_c
    return Point5DDto(
        x=tmp_x,
        y=tmp_y,
        z=tmp_z,
        t=tmp_t,
        c=tmp_c,
    )


@dataclass
class Point5DDto(DataTransferObject):
    x: int
    y: int
    z: int
    t: int
    c: int

    @classmethod
    def from_point5d(cls, point: Point5D) -> "Point5DDto":
        return Point5DDto(x=point.x, y=point.y, z=point.z, t=point.t, c=point.c)

    def to_point5d(self) -> Point5D:
        return Point5D(x=self.x, y=self.y, z=self.z, t=self.t, c=self.c)

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "Point5DDto",
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "t": self.t,
            "c": self.c,
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "Point5DDto | MessageParsingError":
        return parse_as_Point5DDto(value)


def parse_as_Shape5DDto(value: JsonValue) -> "Shape5DDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(f"Could not parse {json.dumps(value)} as Shape5DDto")
    if value.get("__class__") != "Shape5DDto":
        return MessageParsingError(f"Could not parse {json.dumps(value)} as Shape5DDto")
    tmp_x = parse_as_int(value.get("x"))
    if isinstance(tmp_x, MessageParsingError):
        return tmp_x
    tmp_y = parse_as_int(value.get("y"))
    if isinstance(tmp_y, MessageParsingError):
        return tmp_y
    tmp_z = parse_as_int(value.get("z"))
    if isinstance(tmp_z, MessageParsingError):
        return tmp_z
    tmp_t = parse_as_int(value.get("t"))
    if isinstance(tmp_t, MessageParsingError):
        return tmp_t
    tmp_c = parse_as_int(value.get("c"))
    if isinstance(tmp_c, MessageParsingError):
        return tmp_c
    return Shape5DDto(
        x=tmp_x,
        y=tmp_y,
        z=tmp_z,
        t=tmp_t,
        c=tmp_c,
    )


@dataclass
class Shape5DDto(Point5DDto):
    @classmethod
    def from_shape5d(cls, shape: Shape5D) -> "Shape5DDto":
        return Shape5DDto(x=shape.x, y=shape.y, z=shape.z, t=shape.t, c=shape.c)

    def to_shape5d(self) -> Shape5D:
        return Shape5D(x=self.x, y=self.y, z=self.z, t=self.t, c=self.c)

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "Shape5DDto",
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "t": self.t,
            "c": self.c,
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "Shape5DDto | MessageParsingError":
        return parse_as_Shape5DDto(value)


def parse_as_Interval5DDto(value: JsonValue) -> "Interval5DDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as Interval5DDto"
        )
    if value.get("__class__") != "Interval5DDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as Interval5DDto"
        )
    tmp_start = parse_as_Point5DDto(value.get("start"))
    if isinstance(tmp_start, MessageParsingError):
        return tmp_start
    tmp_stop = parse_as_Point5DDto(value.get("stop"))
    if isinstance(tmp_stop, MessageParsingError):
        return tmp_stop
    return Interval5DDto(
        start=tmp_start,
        stop=tmp_stop,
    )


@dataclass
class Interval5DDto(DataTransferObject):
    start: Point5DDto
    stop: Point5DDto

    @classmethod
    def from_interval5d(cls, interval: Interval5D) -> "Interval5DDto":
        return Interval5DDto(
            start=Point5DDto.from_point5d(interval.start),
            stop=Point5DDto.from_point5d(interval.stop),
        )

    def to_interval5d(self) -> Interval5D:
        return Interval5D.create_from_start_stop(
            start=self.start.to_point5d(), stop=self.stop.to_point5d()
        )

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "Interval5DDto",
            "start": self.start.to_json_value(),
            "stop": self.stop.to_json_value(),
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "Interval5DDto | MessageParsingError":
        return parse_as_Interval5DDto(value)


def parse_as_OsfsDto(value: JsonValue) -> "OsfsDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(f"Could not parse {json.dumps(value)} as OsfsDto")
    if value.get("__class__") != "OsfsDto":
        return MessageParsingError(f"Could not parse {json.dumps(value)} as OsfsDto")
    return OsfsDto()


@dataclass
class OsfsDto(DataTransferObject):
    pass

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "OsfsDto",
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "OsfsDto | MessageParsingError":
        return parse_as_OsfsDto(value)


def parse_as_Literal_of__quote_http_quote_0_quote_https_quote__endof_(
    value: JsonValue,
) -> "Literal['http', 'https'] | MessageParsingError":
    tmp_0 = parse_as_str(value)
    if not isinstance(tmp_0, MessageParsingError) and tmp_0 == "http":
        return tmp_0
    tmp_1 = parse_as_str(value)
    if not isinstance(tmp_1, MessageParsingError) and tmp_1 == "https":
        return tmp_1
    return MessageParsingError(f"Could not parse {value} as Literal['http', 'https']")


def parse_as_HttpFsDto(value: JsonValue) -> "HttpFsDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(f"Could not parse {json.dumps(value)} as HttpFsDto")
    if value.get("__class__") != "HttpFsDto":
        return MessageParsingError(f"Could not parse {json.dumps(value)} as HttpFsDto")
    tmp_protocol = parse_as_Literal_of__quote_http_quote_0_quote_https_quote__endof_(
        value.get("protocol")
    )
    if isinstance(tmp_protocol, MessageParsingError):
        return tmp_protocol
    tmp_hostname = parse_as_str(value.get("hostname"))
    if isinstance(tmp_hostname, MessageParsingError):
        return tmp_hostname
    tmp_port = parse_as_Union_of_int0None_endof_(value.get("port"))
    if isinstance(tmp_port, MessageParsingError):
        return tmp_port
    tmp_path = parse_as_str(value.get("path"))
    if isinstance(tmp_path, MessageParsingError):
        return tmp_path
    tmp_search = parse_as_Union_of_Mapping_of_str0str_endof_0None_endof_(
        value.get("search")
    )
    if isinstance(tmp_search, MessageParsingError):
        return tmp_search
    return HttpFsDto(
        protocol=tmp_protocol,
        hostname=tmp_hostname,
        port=tmp_port,
        path=tmp_path,
        search=tmp_search,
    )


@dataclass
class HttpFsDto(DataTransferObject):
    protocol: Literal["http", "https"]
    hostname: str
    port: Optional[int]
    path: str
    search: Optional[Mapping[str, str]]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "HttpFsDto",
            "protocol": self.protocol,
            "hostname": self.hostname,
            "port": convert_to_json_value(self.port),
            "path": self.path,
            "search": convert_to_json_value(self.search),
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "HttpFsDto | MessageParsingError":
        return parse_as_HttpFsDto(value)


def parse_as_BucketFSDto(value: JsonValue) -> "BucketFSDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as BucketFSDto"
        )
    if value.get("__class__") != "BucketFSDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as BucketFSDto"
        )
    tmp_bucket_name = parse_as_str(value.get("bucket_name"))
    if isinstance(tmp_bucket_name, MessageParsingError):
        return tmp_bucket_name
    return BucketFSDto(
        bucket_name=tmp_bucket_name,
    )


@dataclass
class BucketFSDto(DataTransferObject):
    bucket_name: str

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "BucketFSDto",
            "bucket_name": self.bucket_name,
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "BucketFSDto | MessageParsingError":
        return parse_as_BucketFSDto(value)


FsDto = Union[OsfsDto, HttpFsDto, BucketFSDto]

DtypeDto = Literal["uint8", "uint16", "uint32", "uint64", "float32"]


def dtype_to_dto(dtype: "np.dtype[Any]") -> DtypeDto:
    return cast(DtypeDto, str(dtype))


def parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(
    value: JsonValue,
) -> "Union[OsfsDto, HttpFsDto, BucketFSDto] | MessageParsingError":
    parsed_option_0 = parse_as_OsfsDto(value)
    if not isinstance(parsed_option_0, MessageParsingError):
        return parsed_option_0
    parsed_option_1 = parse_as_HttpFsDto(value)
    if not isinstance(parsed_option_1, MessageParsingError):
        return parsed_option_1
    parsed_option_2 = parse_as_BucketFSDto(value)
    if not isinstance(parsed_option_2, MessageParsingError):
        return parsed_option_2
    return MessageParsingError(
        f"Could not parse {json.dumps(value)} into Union[OsfsDto, HttpFsDto, BucketFSDto]"
    )


def parse_as_Tuple_of_int0int0int_endof_(
    value: JsonValue,
) -> "Tuple[int, int, int] | MessageParsingError":
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return MessageParsingError(
            f"Could not parse Tuple[int, int, int] from {json.dumps(value)}"
        )
    tmp_0 = parse_as_int(value[0])
    if isinstance(tmp_0, MessageParsingError):
        return tmp_0
    tmp_1 = parse_as_int(value[1])
    if isinstance(tmp_1, MessageParsingError):
        return tmp_1
    tmp_2 = parse_as_int(value[2])
    if isinstance(tmp_2, MessageParsingError):
        return tmp_2
    return (
        tmp_0,
        tmp_1,
        tmp_2,
    )


def parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_float32_quote__endof_(
    value: JsonValue,
) -> "Literal['uint8', 'uint16', 'uint32', 'uint64', 'float32'] | MessageParsingError":
    tmp_0 = parse_as_str(value)
    if not isinstance(tmp_0, MessageParsingError) and tmp_0 == "uint8":
        return tmp_0
    tmp_1 = parse_as_str(value)
    if not isinstance(tmp_1, MessageParsingError) and tmp_1 == "uint16":
        return tmp_1
    tmp_2 = parse_as_str(value)
    if not isinstance(tmp_2, MessageParsingError) and tmp_2 == "uint32":
        return tmp_2
    tmp_3 = parse_as_str(value)
    if not isinstance(tmp_3, MessageParsingError) and tmp_3 == "uint64":
        return tmp_3
    tmp_4 = parse_as_str(value)
    if not isinstance(tmp_4, MessageParsingError) and tmp_4 == "float32":
        return tmp_4
    return MessageParsingError(
        f"Could not parse {value} as Literal['uint8', 'uint16', 'uint32', 'uint64', 'float32']"
    )


def parse_as_Literal_of__quote_raw_quote_0_quote_jpeg_quote__endof_(
    value: JsonValue,
) -> "Literal['raw', 'jpeg'] | MessageParsingError":
    tmp_0 = parse_as_str(value)
    if not isinstance(tmp_0, MessageParsingError) and tmp_0 == "raw":
        return tmp_0
    tmp_1 = parse_as_str(value)
    if not isinstance(tmp_1, MessageParsingError) and tmp_1 == "jpeg":
        return tmp_1
    return MessageParsingError(f"Could not parse {value} as Literal['raw', 'jpeg']")


def parse_as_PrecomputedChunksDataSourceDto(
    value: JsonValue,
) -> "PrecomputedChunksDataSourceDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as PrecomputedChunksDataSourceDto"
        )
    if value.get("__class__") != "PrecomputedChunksDataSourceDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as PrecomputedChunksDataSourceDto"
        )
    tmp_url = parse_as_UrlDto(value.get("url"))
    if isinstance(tmp_url, MessageParsingError):
        return tmp_url
    tmp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(
        value.get("filesystem")
    )
    if isinstance(tmp_filesystem, MessageParsingError):
        return tmp_filesystem
    tmp_path = parse_as_str(value.get("path"))
    if isinstance(tmp_path, MessageParsingError):
        return tmp_path
    tmp_scale_key = parse_as_str(value.get("scale_key"))
    if isinstance(tmp_scale_key, MessageParsingError):
        return tmp_scale_key
    tmp_interval = parse_as_Interval5DDto(value.get("interval"))
    if isinstance(tmp_interval, MessageParsingError):
        return tmp_interval
    tmp_tile_shape = parse_as_Shape5DDto(value.get("tile_shape"))
    if isinstance(tmp_tile_shape, MessageParsingError):
        return tmp_tile_shape
    tmp_spatial_resolution = parse_as_Tuple_of_int0int0int_endof_(
        value.get("spatial_resolution")
    )
    if isinstance(tmp_spatial_resolution, MessageParsingError):
        return tmp_spatial_resolution
    tmp_dtype = parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_float32_quote__endof_(
        value.get("dtype")
    )
    if isinstance(tmp_dtype, MessageParsingError):
        return tmp_dtype
    tmp_encoder = parse_as_Literal_of__quote_raw_quote_0_quote_jpeg_quote__endof_(
        value.get("encoder")
    )
    if isinstance(tmp_encoder, MessageParsingError):
        return tmp_encoder
    return PrecomputedChunksDataSourceDto(
        url=tmp_url,
        filesystem=tmp_filesystem,
        path=tmp_path,
        scale_key=tmp_scale_key,
        interval=tmp_interval,
        tile_shape=tmp_tile_shape,
        spatial_resolution=tmp_spatial_resolution,
        dtype=tmp_dtype,
        encoder=tmp_encoder,
    )


@dataclass
class PrecomputedChunksDataSourceDto(DataTransferObject):
    url: UrlDto
    filesystem: FsDto
    path: str
    scale_key: str
    interval: Interval5DDto
    tile_shape: Shape5DDto
    spatial_resolution: Tuple[int, int, int]
    dtype: DtypeDto
    encoder: Literal["raw", "jpeg"]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "PrecomputedChunksDataSourceDto",
            "url": self.url.to_json_value(),
            "filesystem": convert_to_json_value(self.filesystem),
            "path": self.path,
            "scale_key": self.scale_key,
            "interval": self.interval.to_json_value(),
            "tile_shape": self.tile_shape.to_json_value(),
            "spatial_resolution": (
                self.spatial_resolution[0],
                self.spatial_resolution[1],
                self.spatial_resolution[2],
            ),
            "dtype": self.dtype,
            "encoder": self.encoder,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "PrecomputedChunksDataSourceDto | MessageParsingError":
        return parse_as_PrecomputedChunksDataSourceDto(value)


def parse_as_N5DataSourceDto(
    value: JsonValue,
) -> "N5DataSourceDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as N5DataSourceDto"
        )
    if value.get("__class__") != "N5DataSourceDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as N5DataSourceDto"
        )
    tmp_url = parse_as_UrlDto(value.get("url"))
    if isinstance(tmp_url, MessageParsingError):
        return tmp_url
    tmp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(
        value.get("filesystem")
    )
    if isinstance(tmp_filesystem, MessageParsingError):
        return tmp_filesystem
    tmp_path = parse_as_str(value.get("path"))
    if isinstance(tmp_path, MessageParsingError):
        return tmp_path
    tmp_interval = parse_as_Interval5DDto(value.get("interval"))
    if isinstance(tmp_interval, MessageParsingError):
        return tmp_interval
    tmp_tile_shape = parse_as_Shape5DDto(value.get("tile_shape"))
    if isinstance(tmp_tile_shape, MessageParsingError):
        return tmp_tile_shape
    tmp_spatial_resolution = parse_as_Tuple_of_int0int0int_endof_(
        value.get("spatial_resolution")
    )
    if isinstance(tmp_spatial_resolution, MessageParsingError):
        return tmp_spatial_resolution
    tmp_dtype = parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_float32_quote__endof_(
        value.get("dtype")
    )
    if isinstance(tmp_dtype, MessageParsingError):
        return tmp_dtype
    return N5DataSourceDto(
        url=tmp_url,
        filesystem=tmp_filesystem,
        path=tmp_path,
        interval=tmp_interval,
        tile_shape=tmp_tile_shape,
        spatial_resolution=tmp_spatial_resolution,
        dtype=tmp_dtype,
    )


@dataclass
class N5DataSourceDto(DataTransferObject):
    url: UrlDto
    filesystem: FsDto
    path: str
    interval: Interval5DDto
    tile_shape: Shape5DDto
    spatial_resolution: Tuple[int, int, int]
    dtype: DtypeDto

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "N5DataSourceDto",
            "url": self.url.to_json_value(),
            "filesystem": convert_to_json_value(self.filesystem),
            "path": self.path,
            "interval": self.interval.to_json_value(),
            "tile_shape": self.tile_shape.to_json_value(),
            "spatial_resolution": (
                self.spatial_resolution[0],
                self.spatial_resolution[1],
                self.spatial_resolution[2],
            ),
            "dtype": self.dtype,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "N5DataSourceDto | MessageParsingError":
        return parse_as_N5DataSourceDto(value)


def parse_as_SkimageDataSourceDto(
    value: JsonValue,
) -> "SkimageDataSourceDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as SkimageDataSourceDto"
        )
    if value.get("__class__") != "SkimageDataSourceDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as SkimageDataSourceDto"
        )
    tmp_url = parse_as_UrlDto(value.get("url"))
    if isinstance(tmp_url, MessageParsingError):
        return tmp_url
    tmp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(
        value.get("filesystem")
    )
    if isinstance(tmp_filesystem, MessageParsingError):
        return tmp_filesystem
    tmp_path = parse_as_str(value.get("path"))
    if isinstance(tmp_path, MessageParsingError):
        return tmp_path
    tmp_interval = parse_as_Interval5DDto(value.get("interval"))
    if isinstance(tmp_interval, MessageParsingError):
        return tmp_interval
    tmp_tile_shape = parse_as_Shape5DDto(value.get("tile_shape"))
    if isinstance(tmp_tile_shape, MessageParsingError):
        return tmp_tile_shape
    tmp_spatial_resolution = parse_as_Tuple_of_int0int0int_endof_(
        value.get("spatial_resolution")
    )
    if isinstance(tmp_spatial_resolution, MessageParsingError):
        return tmp_spatial_resolution
    tmp_dtype = parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_float32_quote__endof_(
        value.get("dtype")
    )
    if isinstance(tmp_dtype, MessageParsingError):
        return tmp_dtype
    return SkimageDataSourceDto(
        url=tmp_url,
        filesystem=tmp_filesystem,
        path=tmp_path,
        interval=tmp_interval,
        tile_shape=tmp_tile_shape,
        spatial_resolution=tmp_spatial_resolution,
        dtype=tmp_dtype,
    )


@dataclass
class SkimageDataSourceDto(DataTransferObject):
    url: UrlDto
    filesystem: FsDto
    path: str
    interval: Interval5DDto
    tile_shape: Shape5DDto
    spatial_resolution: Tuple[int, int, int]
    dtype: DtypeDto

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "SkimageDataSourceDto",
            "url": self.url.to_json_value(),
            "filesystem": convert_to_json_value(self.filesystem),
            "path": self.path,
            "interval": self.interval.to_json_value(),
            "tile_shape": self.tile_shape.to_json_value(),
            "spatial_resolution": (
                self.spatial_resolution[0],
                self.spatial_resolution[1],
                self.spatial_resolution[2],
            ),
            "dtype": self.dtype,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "SkimageDataSourceDto | MessageParsingError":
        return parse_as_SkimageDataSourceDto(value)


FsDataSourceDto = Union[
    PrecomputedChunksDataSourceDto, N5DataSourceDto, SkimageDataSourceDto
]


def parse_as_PrecomputedChunksSinkDto(
    value: JsonValue,
) -> "PrecomputedChunksSinkDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as PrecomputedChunksSinkDto"
        )
    if value.get("__class__") != "PrecomputedChunksSinkDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as PrecomputedChunksSinkDto"
        )
    tmp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(
        value.get("filesystem")
    )
    if isinstance(tmp_filesystem, MessageParsingError):
        return tmp_filesystem
    tmp_path = parse_as_str(value.get("path"))
    if isinstance(tmp_path, MessageParsingError):
        return tmp_path
    tmp_tile_shape = parse_as_Shape5DDto(value.get("tile_shape"))
    if isinstance(tmp_tile_shape, MessageParsingError):
        return tmp_tile_shape
    tmp_interval = parse_as_Interval5DDto(value.get("interval"))
    if isinstance(tmp_interval, MessageParsingError):
        return tmp_interval
    tmp_dtype = parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_float32_quote__endof_(
        value.get("dtype")
    )
    if isinstance(tmp_dtype, MessageParsingError):
        return tmp_dtype
    tmp_scale_key = parse_as_str(value.get("scale_key"))
    if isinstance(tmp_scale_key, MessageParsingError):
        return tmp_scale_key
    tmp_resolution = parse_as_Tuple_of_int0int0int_endof_(value.get("resolution"))
    if isinstance(tmp_resolution, MessageParsingError):
        return tmp_resolution
    tmp_encoding = parse_as_Literal_of__quote_raw_quote_0_quote_jpeg_quote__endof_(
        value.get("encoding")
    )
    if isinstance(tmp_encoding, MessageParsingError):
        return tmp_encoding
    return PrecomputedChunksSinkDto(
        filesystem=tmp_filesystem,
        path=tmp_path,
        tile_shape=tmp_tile_shape,
        interval=tmp_interval,
        dtype=tmp_dtype,
        scale_key=tmp_scale_key,
        resolution=tmp_resolution,
        encoding=tmp_encoding,
    )


@dataclass
class PrecomputedChunksSinkDto(DataTransferObject):
    filesystem: Union[OsfsDto, HttpFsDto, BucketFSDto]
    path: str  # FIXME?
    tile_shape: Shape5DDto
    interval: Interval5DDto
    dtype: DtypeDto
    scale_key: str  # fixme?
    resolution: Tuple[int, int, int]
    encoding: Literal["raw", "jpeg"]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "PrecomputedChunksSinkDto",
            "filesystem": convert_to_json_value(self.filesystem),
            "path": self.path,
            "tile_shape": self.tile_shape.to_json_value(),
            "interval": self.interval.to_json_value(),
            "dtype": self.dtype,
            "scale_key": self.scale_key,
            "resolution": (
                self.resolution[0],
                self.resolution[1],
                self.resolution[2],
            ),
            "encoding": self.encoding,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "PrecomputedChunksSinkDto | MessageParsingError":
        return parse_as_PrecomputedChunksSinkDto(value)


def parse_as_N5GzipCompressorDto(
    value: JsonValue,
) -> "N5GzipCompressorDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as N5GzipCompressorDto"
        )
    if value.get("__class__") != "N5GzipCompressorDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as N5GzipCompressorDto"
        )
    tmp_level = parse_as_int(value.get("level"))
    if isinstance(tmp_level, MessageParsingError):
        return tmp_level
    return N5GzipCompressorDto(
        level=tmp_level,
    )


@dataclass
class N5GzipCompressorDto(DataTransferObject):
    level: int

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "N5GzipCompressorDto",
            "level": self.level,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "N5GzipCompressorDto | MessageParsingError":
        return parse_as_N5GzipCompressorDto(value)


def parse_as_N5Bzip2CompressorDto(
    value: JsonValue,
) -> "N5Bzip2CompressorDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as N5Bzip2CompressorDto"
        )
    if value.get("__class__") != "N5Bzip2CompressorDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as N5Bzip2CompressorDto"
        )
    tmp_blockSize = parse_as_int(value.get("blockSize"))
    if isinstance(tmp_blockSize, MessageParsingError):
        return tmp_blockSize
    return N5Bzip2CompressorDto(
        blockSize=tmp_blockSize,
    )


@dataclass
class N5Bzip2CompressorDto(DataTransferObject):
    blockSize: int

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "N5Bzip2CompressorDto",
            "blockSize": self.blockSize,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "N5Bzip2CompressorDto | MessageParsingError":
        return parse_as_N5Bzip2CompressorDto(value)


def parse_as_N5XzCompressorDto(
    value: JsonValue,
) -> "N5XzCompressorDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as N5XzCompressorDto"
        )
    if value.get("__class__") != "N5XzCompressorDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as N5XzCompressorDto"
        )
    tmp_preset = parse_as_int(value.get("preset"))
    if isinstance(tmp_preset, MessageParsingError):
        return tmp_preset
    return N5XzCompressorDto(
        preset=tmp_preset,
    )


@dataclass
class N5XzCompressorDto(DataTransferObject):
    preset: int

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "N5XzCompressorDto",
            "preset": self.preset,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "N5XzCompressorDto | MessageParsingError":
        return parse_as_N5XzCompressorDto(value)


def parse_as_N5RawCompressorDto(
    value: JsonValue,
) -> "N5RawCompressorDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as N5RawCompressorDto"
        )
    if value.get("__class__") != "N5RawCompressorDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as N5RawCompressorDto"
        )
    return N5RawCompressorDto()


@dataclass
class N5RawCompressorDto(DataTransferObject):
    pass

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "N5RawCompressorDto",
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "N5RawCompressorDto | MessageParsingError":
        return parse_as_N5RawCompressorDto(value)


N5CompressorDto = Union[
    N5GzipCompressorDto, N5Bzip2CompressorDto, N5XzCompressorDto, N5RawCompressorDto
]


def parse_as_Union_of_N5GzipCompressorDto0N5Bzip2CompressorDto0N5XzCompressorDto0N5RawCompressorDto_endof_(
    value: JsonValue,
) -> "Union[N5GzipCompressorDto, N5Bzip2CompressorDto, N5XzCompressorDto, N5RawCompressorDto] | MessageParsingError":
    parsed_option_0 = parse_as_N5GzipCompressorDto(value)
    if not isinstance(parsed_option_0, MessageParsingError):
        return parsed_option_0
    parsed_option_1 = parse_as_N5Bzip2CompressorDto(value)
    if not isinstance(parsed_option_1, MessageParsingError):
        return parsed_option_1
    parsed_option_2 = parse_as_N5XzCompressorDto(value)
    if not isinstance(parsed_option_2, MessageParsingError):
        return parsed_option_2
    parsed_option_3 = parse_as_N5RawCompressorDto(value)
    if not isinstance(parsed_option_3, MessageParsingError):
        return parsed_option_3
    return MessageParsingError(
        f"Could not parse {json.dumps(value)} into Union[N5GzipCompressorDto, N5Bzip2CompressorDto, N5XzCompressorDto, N5RawCompressorDto]"
    )


def parse_as_N5DataSinkDto(value: JsonValue) -> "N5DataSinkDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as N5DataSinkDto"
        )
    if value.get("__class__") != "N5DataSinkDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as N5DataSinkDto"
        )
    tmp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(
        value.get("filesystem")
    )
    if isinstance(tmp_filesystem, MessageParsingError):
        return tmp_filesystem
    tmp_outer_path = parse_as_str(value.get("outer_path"))
    if isinstance(tmp_outer_path, MessageParsingError):
        return tmp_outer_path
    tmp_inner_path = parse_as_str(value.get("inner_path"))
    if isinstance(tmp_inner_path, MessageParsingError):
        return tmp_inner_path
    tmp_interval = parse_as_Interval5DDto(value.get("interval"))
    if isinstance(tmp_interval, MessageParsingError):
        return tmp_interval
    tmp_tile_shape = parse_as_Shape5DDto(value.get("tile_shape"))
    if isinstance(tmp_tile_shape, MessageParsingError):
        return tmp_tile_shape
    tmp_c_axiskeys = parse_as_str(value.get("c_axiskeys"))
    if isinstance(tmp_c_axiskeys, MessageParsingError):
        return tmp_c_axiskeys
    tmp_dtype = parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_float32_quote__endof_(
        value.get("dtype")
    )
    if isinstance(tmp_dtype, MessageParsingError):
        return tmp_dtype
    tmp_compressor = parse_as_Union_of_N5GzipCompressorDto0N5Bzip2CompressorDto0N5XzCompressorDto0N5RawCompressorDto_endof_(
        value.get("compressor")
    )
    if isinstance(tmp_compressor, MessageParsingError):
        return tmp_compressor
    return N5DataSinkDto(
        filesystem=tmp_filesystem,
        outer_path=tmp_outer_path,
        inner_path=tmp_inner_path,
        interval=tmp_interval,
        tile_shape=tmp_tile_shape,
        c_axiskeys=tmp_c_axiskeys,
        dtype=tmp_dtype,
        compressor=tmp_compressor,
    )


@dataclass
class N5DataSinkDto(DataTransferObject):
    filesystem: FsDto
    outer_path: str
    inner_path: str
    interval: Interval5DDto
    tile_shape: Shape5DDto
    c_axiskeys: str
    dtype: DtypeDto
    compressor: N5CompressorDto

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "N5DataSinkDto",
            "filesystem": convert_to_json_value(self.filesystem),
            "outer_path": self.outer_path,
            "inner_path": self.inner_path,
            "interval": self.interval.to_json_value(),
            "tile_shape": self.tile_shape.to_json_value(),
            "c_axiskeys": self.c_axiskeys,
            "dtype": self.dtype,
            "compressor": convert_to_json_value(self.compressor),
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "N5DataSinkDto | MessageParsingError":
        return parse_as_N5DataSinkDto(value)


DataSinkDto = Union[PrecomputedChunksSinkDto, N5DataSinkDto]


def parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto_endof_(
    value: JsonValue,
) -> "Union[PrecomputedChunksDataSourceDto, N5DataSourceDto, SkimageDataSourceDto] | MessageParsingError":
    parsed_option_0 = parse_as_PrecomputedChunksDataSourceDto(value)
    if not isinstance(parsed_option_0, MessageParsingError):
        return parsed_option_0
    parsed_option_1 = parse_as_N5DataSourceDto(value)
    if not isinstance(parsed_option_1, MessageParsingError):
        return parsed_option_1
    parsed_option_2 = parse_as_SkimageDataSourceDto(value)
    if not isinstance(parsed_option_2, MessageParsingError):
        return parsed_option_2
    return MessageParsingError(
        f"Could not parse {json.dumps(value)} into Union[PrecomputedChunksDataSourceDto, N5DataSourceDto, SkimageDataSourceDto]"
    )


def parse_as_Tuple_of_Tuple_of_int0int0int_endof_0_varlen__endof_(
    value: JsonValue,
) -> "Tuple[Tuple[int, int, int], ...] | MessageParsingError":
    if not isinstance(value, (list, tuple)):
        return MessageParsingError(
            f"Could not parse Tuple[Tuple[int, int, int], ...] from {json.dumps(value)}"
        )
    items: List[Tuple[int, int, int]] = []
    for item in value:
        parsed = parse_as_Tuple_of_int0int0int_endof_(item)
        if isinstance(parsed, MessageParsingError):
            return parsed
        items.append(parsed)
    return tuple(items)


def parse_as_PixelAnnotationDto(
    value: JsonValue,
) -> "PixelAnnotationDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as PixelAnnotationDto"
        )
    if value.get("__class__") != "PixelAnnotationDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as PixelAnnotationDto"
        )
    tmp_raw_data = parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto_endof_(
        value.get("raw_data")
    )
    if isinstance(tmp_raw_data, MessageParsingError):
        return tmp_raw_data
    tmp_points = parse_as_Tuple_of_Tuple_of_int0int0int_endof_0_varlen__endof_(
        value.get("points")
    )
    if isinstance(tmp_points, MessageParsingError):
        return tmp_points
    return PixelAnnotationDto(
        raw_data=tmp_raw_data,
        points=tmp_points,
    )


@dataclass
class PixelAnnotationDto(DataTransferObject):
    raw_data: FsDataSourceDto
    points: Tuple[Tuple[int, int, int], ...]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "PixelAnnotationDto",
            "raw_data": convert_to_json_value(self.raw_data),
            "points": tuple(
                (
                    item[0],
                    item[1],
                    item[2],
                )
                for item in self.points
            ),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "PixelAnnotationDto | MessageParsingError":
        return parse_as_PixelAnnotationDto(value)


def parse_as_RpcErrorDto(value: JsonValue) -> "RpcErrorDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as RpcErrorDto"
        )
    if value.get("__class__") != "RpcErrorDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as RpcErrorDto"
        )
    tmp_error = parse_as_str(value.get("error"))
    if isinstance(tmp_error, MessageParsingError):
        return tmp_error
    return RpcErrorDto(
        error=tmp_error,
    )


@dataclass
class RpcErrorDto(DataTransferObject):
    error: str

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "RpcErrorDto",
            "error": self.error,
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "RpcErrorDto | MessageParsingError":
        return parse_as_RpcErrorDto(value)


def parse_as_RecolorLabelParams(
    value: JsonValue,
) -> "RecolorLabelParams | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as RecolorLabelParams"
        )
    if value.get("__class__") != "RecolorLabelParams":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as RecolorLabelParams"
        )
    tmp_label_name = parse_as_str(value.get("label_name"))
    if isinstance(tmp_label_name, MessageParsingError):
        return tmp_label_name
    tmp_new_color = parse_as_ColorDto(value.get("new_color"))
    if isinstance(tmp_new_color, MessageParsingError):
        return tmp_new_color
    return RecolorLabelParams(
        label_name=tmp_label_name,
        new_color=tmp_new_color,
    )


@dataclass
class RecolorLabelParams(DataTransferObject):
    label_name: str
    new_color: ColorDto

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "RecolorLabelParams",
            "label_name": self.label_name,
            "new_color": self.new_color.to_json_value(),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "RecolorLabelParams | MessageParsingError":
        return parse_as_RecolorLabelParams(value)


def parse_as_RenameLabelParams(
    value: JsonValue,
) -> "RenameLabelParams | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as RenameLabelParams"
        )
    if value.get("__class__") != "RenameLabelParams":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as RenameLabelParams"
        )
    tmp_old_name = parse_as_str(value.get("old_name"))
    if isinstance(tmp_old_name, MessageParsingError):
        return tmp_old_name
    tmp_new_name = parse_as_str(value.get("new_name"))
    if isinstance(tmp_new_name, MessageParsingError):
        return tmp_new_name
    return RenameLabelParams(
        old_name=tmp_old_name,
        new_name=tmp_new_name,
    )


@dataclass
class RenameLabelParams(DataTransferObject):
    old_name: str
    new_name: str

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "RenameLabelParams",
            "old_name": self.old_name,
            "new_name": self.new_name,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "RenameLabelParams | MessageParsingError":
        return parse_as_RenameLabelParams(value)


def parse_as_CreateLabelParams(
    value: JsonValue,
) -> "CreateLabelParams | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as CreateLabelParams"
        )
    if value.get("__class__") != "CreateLabelParams":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as CreateLabelParams"
        )
    tmp_label_name = parse_as_str(value.get("label_name"))
    if isinstance(tmp_label_name, MessageParsingError):
        return tmp_label_name
    tmp_color = parse_as_ColorDto(value.get("color"))
    if isinstance(tmp_color, MessageParsingError):
        return tmp_color
    return CreateLabelParams(
        label_name=tmp_label_name,
        color=tmp_color,
    )


@dataclass
class CreateLabelParams(DataTransferObject):
    label_name: str
    color: ColorDto

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "CreateLabelParams",
            "label_name": self.label_name,
            "color": self.color.to_json_value(),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "CreateLabelParams | MessageParsingError":
        return parse_as_CreateLabelParams(value)


def parse_as_RemoveLabelParams(
    value: JsonValue,
) -> "RemoveLabelParams | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as RemoveLabelParams"
        )
    if value.get("__class__") != "RemoveLabelParams":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as RemoveLabelParams"
        )
    tmp_label_name = parse_as_str(value.get("label_name"))
    if isinstance(tmp_label_name, MessageParsingError):
        return tmp_label_name
    return RemoveLabelParams(
        label_name=tmp_label_name,
    )


@dataclass
class RemoveLabelParams(DataTransferObject):
    label_name: str

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "RemoveLabelParams",
            "label_name": self.label_name,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "RemoveLabelParams | MessageParsingError":
        return parse_as_RemoveLabelParams(value)


def parse_as_AddPixelAnnotationParams(
    value: JsonValue,
) -> "AddPixelAnnotationParams | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as AddPixelAnnotationParams"
        )
    if value.get("__class__") != "AddPixelAnnotationParams":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as AddPixelAnnotationParams"
        )
    tmp_label_name = parse_as_str(value.get("label_name"))
    if isinstance(tmp_label_name, MessageParsingError):
        return tmp_label_name
    tmp_pixel_annotation = parse_as_PixelAnnotationDto(value.get("pixel_annotation"))
    if isinstance(tmp_pixel_annotation, MessageParsingError):
        return tmp_pixel_annotation
    return AddPixelAnnotationParams(
        label_name=tmp_label_name,
        pixel_annotation=tmp_pixel_annotation,
    )


@dataclass
class AddPixelAnnotationParams(DataTransferObject):
    label_name: str
    pixel_annotation: PixelAnnotationDto

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "AddPixelAnnotationParams",
            "label_name": self.label_name,
            "pixel_annotation": self.pixel_annotation.to_json_value(),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "AddPixelAnnotationParams | MessageParsingError":
        return parse_as_AddPixelAnnotationParams(value)


def parse_as_RemovePixelAnnotationParams(
    value: JsonValue,
) -> "RemovePixelAnnotationParams | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as RemovePixelAnnotationParams"
        )
    if value.get("__class__") != "RemovePixelAnnotationParams":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as RemovePixelAnnotationParams"
        )
    tmp_label_name = parse_as_str(value.get("label_name"))
    if isinstance(tmp_label_name, MessageParsingError):
        return tmp_label_name
    tmp_pixel_annotation = parse_as_PixelAnnotationDto(value.get("pixel_annotation"))
    if isinstance(tmp_pixel_annotation, MessageParsingError):
        return tmp_pixel_annotation
    return RemovePixelAnnotationParams(
        label_name=tmp_label_name,
        pixel_annotation=tmp_pixel_annotation,
    )


@dataclass
class RemovePixelAnnotationParams(DataTransferObject):
    label_name: str
    pixel_annotation: PixelAnnotationDto

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "RemovePixelAnnotationParams",
            "label_name": self.label_name,
            "pixel_annotation": self.pixel_annotation.to_json_value(),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "RemovePixelAnnotationParams | MessageParsingError":
        return parse_as_RemovePixelAnnotationParams(value)


def parse_as_Tuple_of_PixelAnnotationDto0_varlen__endof_(
    value: JsonValue,
) -> "Tuple[PixelAnnotationDto, ...] | MessageParsingError":
    if not isinstance(value, (list, tuple)):
        return MessageParsingError(
            f"Could not parse Tuple[PixelAnnotationDto, ...] from {json.dumps(value)}"
        )
    items: List[PixelAnnotationDto] = []
    for item in value:
        parsed = parse_as_PixelAnnotationDto(item)
        if isinstance(parsed, MessageParsingError):
            return parsed
        items.append(parsed)
    return tuple(items)


def parse_as_LabelDto(value: JsonValue) -> "LabelDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(f"Could not parse {json.dumps(value)} as LabelDto")
    if value.get("__class__") != "LabelDto":
        return MessageParsingError(f"Could not parse {json.dumps(value)} as LabelDto")
    tmp_name = parse_as_str(value.get("name"))
    if isinstance(tmp_name, MessageParsingError):
        return tmp_name
    tmp_color = parse_as_ColorDto(value.get("color"))
    if isinstance(tmp_color, MessageParsingError):
        return tmp_color
    tmp_annotations = parse_as_Tuple_of_PixelAnnotationDto0_varlen__endof_(
        value.get("annotations")
    )
    if isinstance(tmp_annotations, MessageParsingError):
        return tmp_annotations
    return LabelDto(
        name=tmp_name,
        color=tmp_color,
        annotations=tmp_annotations,
    )


@dataclass
class LabelDto(DataTransferObject):
    name: str
    color: ColorDto
    annotations: Tuple[PixelAnnotationDto, ...]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "LabelDto",
            "name": self.name,
            "color": self.color.to_json_value(),
            "annotations": tuple(item.to_json_value() for item in self.annotations),
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "LabelDto | MessageParsingError":
        return parse_as_LabelDto(value)


def parse_as_Tuple_of_LabelDto0_varlen__endof_(
    value: JsonValue,
) -> "Tuple[LabelDto, ...] | MessageParsingError":
    if not isinstance(value, (list, tuple)):
        return MessageParsingError(
            f"Could not parse Tuple[LabelDto, ...] from {json.dumps(value)}"
        )
    items: List[LabelDto] = []
    for item in value:
        parsed = parse_as_LabelDto(item)
        if isinstance(parsed, MessageParsingError):
            return parsed
        items.append(parsed)
    return tuple(items)


def parse_as_BrushingAppletStateDto(
    value: JsonValue,
) -> "BrushingAppletStateDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as BrushingAppletStateDto"
        )
    if value.get("__class__") != "BrushingAppletStateDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as BrushingAppletStateDto"
        )
    tmp_labels = parse_as_Tuple_of_LabelDto0_varlen__endof_(value.get("labels"))
    if isinstance(tmp_labels, MessageParsingError):
        return tmp_labels
    return BrushingAppletStateDto(
        labels=tmp_labels,
    )


@dataclass
class BrushingAppletStateDto(DataTransferObject):
    labels: Tuple[LabelDto, ...]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "BrushingAppletStateDto",
            "labels": tuple(item.to_json_value() for item in self.labels),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "BrushingAppletStateDto | MessageParsingError":
        return parse_as_BrushingAppletStateDto(value)


def parse_as_ViewDto(value: JsonValue) -> "ViewDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(f"Could not parse {json.dumps(value)} as ViewDto")
    if value.get("__class__") != "ViewDto":
        return MessageParsingError(f"Could not parse {json.dumps(value)} as ViewDto")
    tmp_name = parse_as_str(value.get("name"))
    if isinstance(tmp_name, MessageParsingError):
        return tmp_name
    tmp_url = parse_as_UrlDto(value.get("url"))
    if isinstance(tmp_url, MessageParsingError):
        return tmp_url
    return ViewDto(
        name=tmp_name,
        url=tmp_url,
    )


@dataclass
class ViewDto(DataTransferObject):
    name: str
    url: UrlDto

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "ViewDto",
            "name": self.name,
            "url": self.url.to_json_value(),
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "ViewDto | MessageParsingError":
        return parse_as_ViewDto(value)


def parse_as_DataView(value: JsonValue) -> "DataView | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(f"Could not parse {json.dumps(value)} as DataView")
    if value.get("__class__") != "DataView":
        return MessageParsingError(f"Could not parse {json.dumps(value)} as DataView")
    tmp_name = parse_as_str(value.get("name"))
    if isinstance(tmp_name, MessageParsingError):
        return tmp_name
    tmp_url = parse_as_UrlDto(value.get("url"))
    if isinstance(tmp_url, MessageParsingError):
        return tmp_url
    return DataView(
        name=tmp_name,
        url=tmp_url,
    )


@dataclass
class DataView(ViewDto):
    pass

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "DataView",
            "name": self.name,
            "url": self.url.to_json_value(),
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "DataView | MessageParsingError":
        return parse_as_DataView(value)


def parse_as_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto_endof_0_varlen__endof_(
    value: JsonValue,
) -> "Tuple[Union[PrecomputedChunksDataSourceDto, N5DataSourceDto, SkimageDataSourceDto], ...] | MessageParsingError":
    if not isinstance(value, (list, tuple)):
        return MessageParsingError(
            f"Could not parse Tuple[Union[PrecomputedChunksDataSourceDto, N5DataSourceDto, SkimageDataSourceDto], ...] from {json.dumps(value)}"
        )
    items: List[
        Union[PrecomputedChunksDataSourceDto, N5DataSourceDto, SkimageDataSourceDto]
    ] = []
    for item in value:
        parsed = parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto_endof_(
            item
        )
        if isinstance(parsed, MessageParsingError):
            return parsed
        items.append(parsed)
    return tuple(items)


def parse_as_RawDataViewDto(value: JsonValue) -> "RawDataViewDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as RawDataViewDto"
        )
    if value.get("__class__") != "RawDataViewDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as RawDataViewDto"
        )
    tmp_name = parse_as_str(value.get("name"))
    if isinstance(tmp_name, MessageParsingError):
        return tmp_name
    tmp_url = parse_as_UrlDto(value.get("url"))
    if isinstance(tmp_url, MessageParsingError):
        return tmp_url
    tmp_datasources = parse_as_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto_endof_0_varlen__endof_(
        value.get("datasources")
    )
    if isinstance(tmp_datasources, MessageParsingError):
        return tmp_datasources
    return RawDataViewDto(
        name=tmp_name,
        url=tmp_url,
        datasources=tmp_datasources,
    )


@dataclass
class RawDataViewDto(ViewDto):
    datasources: Tuple[FsDataSourceDto, ...]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "RawDataViewDto",
            "name": self.name,
            "url": self.url.to_json_value(),
            "datasources": tuple(
                convert_to_json_value(item) for item in self.datasources
            ),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "RawDataViewDto | MessageParsingError":
        return parse_as_RawDataViewDto(value)


def parse_as_StrippedPrecomputedViewDto(
    value: JsonValue,
) -> "StrippedPrecomputedViewDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as StrippedPrecomputedViewDto"
        )
    if value.get("__class__") != "StrippedPrecomputedViewDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as StrippedPrecomputedViewDto"
        )
    tmp_name = parse_as_str(value.get("name"))
    if isinstance(tmp_name, MessageParsingError):
        return tmp_name
    tmp_url = parse_as_UrlDto(value.get("url"))
    if isinstance(tmp_url, MessageParsingError):
        return tmp_url
    tmp_datasource = parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto_endof_(
        value.get("datasource")
    )
    if isinstance(tmp_datasource, MessageParsingError):
        return tmp_datasource
    return StrippedPrecomputedViewDto(
        name=tmp_name,
        url=tmp_url,
        datasource=tmp_datasource,
    )


@dataclass
class StrippedPrecomputedViewDto(ViewDto):
    datasource: FsDataSourceDto

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "StrippedPrecomputedViewDto",
            "name": self.name,
            "url": self.url.to_json_value(),
            "datasource": convert_to_json_value(self.datasource),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "StrippedPrecomputedViewDto | MessageParsingError":
        return parse_as_StrippedPrecomputedViewDto(value)


def parse_as_PredictionsViewDto(
    value: JsonValue,
) -> "PredictionsViewDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as PredictionsViewDto"
        )
    if value.get("__class__") != "PredictionsViewDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as PredictionsViewDto"
        )
    tmp_name = parse_as_str(value.get("name"))
    if isinstance(tmp_name, MessageParsingError):
        return tmp_name
    tmp_url = parse_as_UrlDto(value.get("url"))
    if isinstance(tmp_url, MessageParsingError):
        return tmp_url
    tmp_raw_data = parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto_endof_(
        value.get("raw_data")
    )
    if isinstance(tmp_raw_data, MessageParsingError):
        return tmp_raw_data
    tmp_classifier_generation = parse_as_int(value.get("classifier_generation"))
    if isinstance(tmp_classifier_generation, MessageParsingError):
        return tmp_classifier_generation
    return PredictionsViewDto(
        name=tmp_name,
        url=tmp_url,
        raw_data=tmp_raw_data,
        classifier_generation=tmp_classifier_generation,
    )


@dataclass
class PredictionsViewDto(ViewDto):
    raw_data: FsDataSourceDto
    classifier_generation: int

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "PredictionsViewDto",
            "name": self.name,
            "url": self.url.to_json_value(),
            "raw_data": convert_to_json_value(self.raw_data),
            "classifier_generation": self.classifier_generation,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "PredictionsViewDto | MessageParsingError":
        return parse_as_PredictionsViewDto(value)


def parse_as_FailedViewDto(value: JsonValue) -> "FailedViewDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as FailedViewDto"
        )
    if value.get("__class__") != "FailedViewDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as FailedViewDto"
        )
    tmp_name = parse_as_str(value.get("name"))
    if isinstance(tmp_name, MessageParsingError):
        return tmp_name
    tmp_url = parse_as_UrlDto(value.get("url"))
    if isinstance(tmp_url, MessageParsingError):
        return tmp_url
    tmp_error_message = parse_as_str(value.get("error_message"))
    if isinstance(tmp_error_message, MessageParsingError):
        return tmp_error_message
    return FailedViewDto(
        name=tmp_name,
        url=tmp_url,
        error_message=tmp_error_message,
    )


@dataclass
class FailedViewDto(ViewDto):
    error_message: str

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "FailedViewDto",
            "name": self.name,
            "url": self.url.to_json_value(),
            "error_message": self.error_message,
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "FailedViewDto | MessageParsingError":
        return parse_as_FailedViewDto(value)


def parse_as_UnsupportedDatasetViewDto(
    value: JsonValue,
) -> "UnsupportedDatasetViewDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as UnsupportedDatasetViewDto"
        )
    if value.get("__class__") != "UnsupportedDatasetViewDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as UnsupportedDatasetViewDto"
        )
    tmp_name = parse_as_str(value.get("name"))
    if isinstance(tmp_name, MessageParsingError):
        return tmp_name
    tmp_url = parse_as_UrlDto(value.get("url"))
    if isinstance(tmp_url, MessageParsingError):
        return tmp_url
    return UnsupportedDatasetViewDto(
        name=tmp_name,
        url=tmp_url,
    )


@dataclass
class UnsupportedDatasetViewDto(ViewDto):
    pass

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "UnsupportedDatasetViewDto",
            "name": self.name,
            "url": self.url.to_json_value(),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "UnsupportedDatasetViewDto | MessageParsingError":
        return parse_as_UnsupportedDatasetViewDto(value)


DataViewUnion = Union[
    RawDataViewDto, StrippedPrecomputedViewDto, FailedViewDto, UnsupportedDatasetViewDto
]


def parse_as_Union_of_RawDataViewDto0StrippedPrecomputedViewDto0FailedViewDto0UnsupportedDatasetViewDto_endof_(
    value: JsonValue,
) -> "Union[RawDataViewDto, StrippedPrecomputedViewDto, FailedViewDto, UnsupportedDatasetViewDto] | MessageParsingError":
    parsed_option_0 = parse_as_RawDataViewDto(value)
    if not isinstance(parsed_option_0, MessageParsingError):
        return parsed_option_0
    parsed_option_1 = parse_as_StrippedPrecomputedViewDto(value)
    if not isinstance(parsed_option_1, MessageParsingError):
        return parsed_option_1
    parsed_option_2 = parse_as_FailedViewDto(value)
    if not isinstance(parsed_option_2, MessageParsingError):
        return parsed_option_2
    parsed_option_3 = parse_as_UnsupportedDatasetViewDto(value)
    if not isinstance(parsed_option_3, MessageParsingError):
        return parsed_option_3
    return MessageParsingError(
        f"Could not parse {json.dumps(value)} into Union[RawDataViewDto, StrippedPrecomputedViewDto, FailedViewDto, UnsupportedDatasetViewDto]"
    )


def parse_as_Tuple_of_Union_of_RawDataViewDto0StrippedPrecomputedViewDto0FailedViewDto0UnsupportedDatasetViewDto_endof_0_varlen__endof_(
    value: JsonValue,
) -> "Tuple[Union[RawDataViewDto, StrippedPrecomputedViewDto, FailedViewDto, UnsupportedDatasetViewDto], ...] | MessageParsingError":
    if not isinstance(value, (list, tuple)):
        return MessageParsingError(
            f"Could not parse Tuple[Union[RawDataViewDto, StrippedPrecomputedViewDto, FailedViewDto, UnsupportedDatasetViewDto], ...] from {json.dumps(value)}"
        )
    items: List[
        Union[
            RawDataViewDto,
            StrippedPrecomputedViewDto,
            FailedViewDto,
            UnsupportedDatasetViewDto,
        ]
    ] = []
    for item in value:
        parsed = parse_as_Union_of_RawDataViewDto0StrippedPrecomputedViewDto0FailedViewDto0UnsupportedDatasetViewDto_endof_(
            item
        )
        if isinstance(parsed, MessageParsingError):
            return parsed
        items.append(parsed)
    return tuple(items)


def parse_as_Tuple_of_PredictionsViewDto0_varlen__endof_(
    value: JsonValue,
) -> "Tuple[PredictionsViewDto, ...] | MessageParsingError":
    if not isinstance(value, (list, tuple)):
        return MessageParsingError(
            f"Could not parse Tuple[PredictionsViewDto, ...] from {json.dumps(value)}"
        )
    items: List[PredictionsViewDto] = []
    for item in value:
        parsed = parse_as_PredictionsViewDto(item)
        if isinstance(parsed, MessageParsingError):
            return parsed
        items.append(parsed)
    return tuple(items)


def parse_as_Tuple_of_ColorDto0_varlen__endof_(
    value: JsonValue,
) -> "Tuple[ColorDto, ...] | MessageParsingError":
    if not isinstance(value, (list, tuple)):
        return MessageParsingError(
            f"Could not parse Tuple[ColorDto, ...] from {json.dumps(value)}"
        )
    items: List[ColorDto] = []
    for item in value:
        parsed = parse_as_ColorDto(item)
        if isinstance(parsed, MessageParsingError):
            return parsed
        items.append(parsed)
    return tuple(items)


def parse_as_ViewerAppletStateDto(
    value: JsonValue,
) -> "ViewerAppletStateDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as ViewerAppletStateDto"
        )
    if value.get("__class__") != "ViewerAppletStateDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as ViewerAppletStateDto"
        )
    tmp_frontend_timestamp = parse_as_int(value.get("frontend_timestamp"))
    if isinstance(tmp_frontend_timestamp, MessageParsingError):
        return tmp_frontend_timestamp
    tmp_data_views = parse_as_Tuple_of_Union_of_RawDataViewDto0StrippedPrecomputedViewDto0FailedViewDto0UnsupportedDatasetViewDto_endof_0_varlen__endof_(
        value.get("data_views")
    )
    if isinstance(tmp_data_views, MessageParsingError):
        return tmp_data_views
    tmp_prediction_views = parse_as_Tuple_of_PredictionsViewDto0_varlen__endof_(
        value.get("prediction_views")
    )
    if isinstance(tmp_prediction_views, MessageParsingError):
        return tmp_prediction_views
    tmp_label_colors = parse_as_Tuple_of_ColorDto0_varlen__endof_(
        value.get("label_colors")
    )
    if isinstance(tmp_label_colors, MessageParsingError):
        return tmp_label_colors
    return ViewerAppletStateDto(
        frontend_timestamp=tmp_frontend_timestamp,
        data_views=tmp_data_views,
        prediction_views=tmp_prediction_views,
        label_colors=tmp_label_colors,
    )


@dataclass
class ViewerAppletStateDto(DataTransferObject):
    frontend_timestamp: int
    data_views: Tuple[
        Union[
            RawDataViewDto,
            StrippedPrecomputedViewDto,
            FailedViewDto,
            UnsupportedDatasetViewDto,
        ],
        ...,
    ]
    prediction_views: Tuple[PredictionsViewDto, ...]
    label_colors: Tuple[ColorDto, ...]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "ViewerAppletStateDto",
            "frontend_timestamp": self.frontend_timestamp,
            "data_views": tuple(
                convert_to_json_value(item) for item in self.data_views
            ),
            "prediction_views": tuple(
                item.to_json_value() for item in self.prediction_views
            ),
            "label_colors": tuple(item.to_json_value() for item in self.label_colors),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "ViewerAppletStateDto | MessageParsingError":
        return parse_as_ViewerAppletStateDto(value)


def parse_as_MakeDataViewParams(
    value: JsonValue,
) -> "MakeDataViewParams | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as MakeDataViewParams"
        )
    if value.get("__class__") != "MakeDataViewParams":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as MakeDataViewParams"
        )
    tmp_view_name = parse_as_str(value.get("view_name"))
    if isinstance(tmp_view_name, MessageParsingError):
        return tmp_view_name
    tmp_url = parse_as_UrlDto(value.get("url"))
    if isinstance(tmp_url, MessageParsingError):
        return tmp_url
    return MakeDataViewParams(
        view_name=tmp_view_name,
        url=tmp_url,
    )


@dataclass
class MakeDataViewParams(DataTransferObject):
    view_name: str
    url: UrlDto

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "MakeDataViewParams",
            "view_name": self.view_name,
            "url": self.url.to_json_value(),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "MakeDataViewParams | MessageParsingError":
        return parse_as_MakeDataViewParams(value)


def parse_as_Literal_of__quote_pending_quote_0_quote_running_quote_0_quote_cancelled_quote_0_quote_failed_quote_0_quote_succeeded_quote__endof_(
    value: JsonValue,
) -> "Literal['pending', 'running', 'cancelled', 'failed', 'succeeded'] | MessageParsingError":
    tmp_0 = parse_as_str(value)
    if not isinstance(tmp_0, MessageParsingError) and tmp_0 == "pending":
        return tmp_0
    tmp_1 = parse_as_str(value)
    if not isinstance(tmp_1, MessageParsingError) and tmp_1 == "running":
        return tmp_1
    tmp_2 = parse_as_str(value)
    if not isinstance(tmp_2, MessageParsingError) and tmp_2 == "cancelled":
        return tmp_2
    tmp_3 = parse_as_str(value)
    if not isinstance(tmp_3, MessageParsingError) and tmp_3 == "failed":
        return tmp_3
    tmp_4 = parse_as_str(value)
    if not isinstance(tmp_4, MessageParsingError) and tmp_4 == "succeeded":
        return tmp_4
    return MessageParsingError(
        f"Could not parse {value} as Literal['pending', 'running', 'cancelled', 'failed', 'succeeded']"
    )


def parse_as_JobDto(value: JsonValue) -> "JobDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(f"Could not parse {json.dumps(value)} as JobDto")
    if value.get("__class__") != "JobDto":
        return MessageParsingError(f"Could not parse {json.dumps(value)} as JobDto")
    tmp_name = parse_as_str(value.get("name"))
    if isinstance(tmp_name, MessageParsingError):
        return tmp_name
    tmp_num_args = parse_as_Union_of_int0None_endof_(value.get("num_args"))
    if isinstance(tmp_num_args, MessageParsingError):
        return tmp_num_args
    tmp_uuid = parse_as_str(value.get("uuid"))
    if isinstance(tmp_uuid, MessageParsingError):
        return tmp_uuid
    tmp_status = parse_as_Literal_of__quote_pending_quote_0_quote_running_quote_0_quote_cancelled_quote_0_quote_failed_quote_0_quote_succeeded_quote__endof_(
        value.get("status")
    )
    if isinstance(tmp_status, MessageParsingError):
        return tmp_status
    tmp_num_completed_steps = parse_as_int(value.get("num_completed_steps"))
    if isinstance(tmp_num_completed_steps, MessageParsingError):
        return tmp_num_completed_steps
    tmp_error_message = parse_as_Union_of_str0None_endof_(value.get("error_message"))
    if isinstance(tmp_error_message, MessageParsingError):
        return tmp_error_message
    return JobDto(
        name=tmp_name,
        num_args=tmp_num_args,
        uuid=tmp_uuid,
        status=tmp_status,
        num_completed_steps=tmp_num_completed_steps,
        error_message=tmp_error_message,
    )


@dataclass
class JobDto(DataTransferObject):
    name: str
    num_args: Optional[int]
    uuid: str
    status: Literal["pending", "running", "cancelled", "failed", "succeeded"]
    num_completed_steps: int
    error_message: Optional[str]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "JobDto",
            "name": self.name,
            "num_args": convert_to_json_value(self.num_args),
            "uuid": self.uuid,
            "status": self.status,
            "num_completed_steps": self.num_completed_steps,
            "error_message": convert_to_json_value(self.error_message),
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "JobDto | MessageParsingError":
        return parse_as_JobDto(value)


def parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto_endof_(
    value: JsonValue,
) -> "Union[PrecomputedChunksSinkDto, N5DataSinkDto] | MessageParsingError":
    parsed_option_0 = parse_as_PrecomputedChunksSinkDto(value)
    if not isinstance(parsed_option_0, MessageParsingError):
        return parsed_option_0
    parsed_option_1 = parse_as_N5DataSinkDto(value)
    if not isinstance(parsed_option_1, MessageParsingError):
        return parsed_option_1
    return MessageParsingError(
        f"Could not parse {json.dumps(value)} into Union[PrecomputedChunksSinkDto, N5DataSinkDto]"
    )


def parse_as_ExportJobDto(value: JsonValue) -> "ExportJobDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as ExportJobDto"
        )
    if value.get("__class__") != "ExportJobDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as ExportJobDto"
        )
    tmp_name = parse_as_str(value.get("name"))
    if isinstance(tmp_name, MessageParsingError):
        return tmp_name
    tmp_num_args = parse_as_Union_of_int0None_endof_(value.get("num_args"))
    if isinstance(tmp_num_args, MessageParsingError):
        return tmp_num_args
    tmp_uuid = parse_as_str(value.get("uuid"))
    if isinstance(tmp_uuid, MessageParsingError):
        return tmp_uuid
    tmp_status = parse_as_Literal_of__quote_pending_quote_0_quote_running_quote_0_quote_cancelled_quote_0_quote_failed_quote_0_quote_succeeded_quote__endof_(
        value.get("status")
    )
    if isinstance(tmp_status, MessageParsingError):
        return tmp_status
    tmp_num_completed_steps = parse_as_int(value.get("num_completed_steps"))
    if isinstance(tmp_num_completed_steps, MessageParsingError):
        return tmp_num_completed_steps
    tmp_error_message = parse_as_Union_of_str0None_endof_(value.get("error_message"))
    if isinstance(tmp_error_message, MessageParsingError):
        return tmp_error_message
    tmp_datasink = parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto_endof_(
        value.get("datasink")
    )
    if isinstance(tmp_datasink, MessageParsingError):
        return tmp_datasink
    return ExportJobDto(
        name=tmp_name,
        num_args=tmp_num_args,
        uuid=tmp_uuid,
        status=tmp_status,
        num_completed_steps=tmp_num_completed_steps,
        error_message=tmp_error_message,
        datasink=tmp_datasink,
    )


@dataclass
class ExportJobDto(JobDto):
    datasink: DataSinkDto

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "ExportJobDto",
            "name": self.name,
            "num_args": convert_to_json_value(self.num_args),
            "uuid": self.uuid,
            "status": self.status,
            "num_completed_steps": self.num_completed_steps,
            "error_message": convert_to_json_value(self.error_message),
            "datasink": convert_to_json_value(self.datasink),
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "ExportJobDto | MessageParsingError":
        return parse_as_ExportJobDto(value)


def parse_as_OpenDatasinkJobDto(
    value: JsonValue,
) -> "OpenDatasinkJobDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as OpenDatasinkJobDto"
        )
    if value.get("__class__") != "OpenDatasinkJobDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as OpenDatasinkJobDto"
        )
    tmp_name = parse_as_str(value.get("name"))
    if isinstance(tmp_name, MessageParsingError):
        return tmp_name
    tmp_num_args = parse_as_Union_of_int0None_endof_(value.get("num_args"))
    if isinstance(tmp_num_args, MessageParsingError):
        return tmp_num_args
    tmp_uuid = parse_as_str(value.get("uuid"))
    if isinstance(tmp_uuid, MessageParsingError):
        return tmp_uuid
    tmp_status = parse_as_Literal_of__quote_pending_quote_0_quote_running_quote_0_quote_cancelled_quote_0_quote_failed_quote_0_quote_succeeded_quote__endof_(
        value.get("status")
    )
    if isinstance(tmp_status, MessageParsingError):
        return tmp_status
    tmp_num_completed_steps = parse_as_int(value.get("num_completed_steps"))
    if isinstance(tmp_num_completed_steps, MessageParsingError):
        return tmp_num_completed_steps
    tmp_error_message = parse_as_Union_of_str0None_endof_(value.get("error_message"))
    if isinstance(tmp_error_message, MessageParsingError):
        return tmp_error_message
    tmp_datasink = parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto_endof_(
        value.get("datasink")
    )
    if isinstance(tmp_datasink, MessageParsingError):
        return tmp_datasink
    return OpenDatasinkJobDto(
        name=tmp_name,
        num_args=tmp_num_args,
        uuid=tmp_uuid,
        status=tmp_status,
        num_completed_steps=tmp_num_completed_steps,
        error_message=tmp_error_message,
        datasink=tmp_datasink,
    )


@dataclass
class OpenDatasinkJobDto(JobDto):
    datasink: DataSinkDto

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "OpenDatasinkJobDto",
            "name": self.name,
            "num_args": convert_to_json_value(self.num_args),
            "uuid": self.uuid,
            "status": self.status,
            "num_completed_steps": self.num_completed_steps,
            "error_message": convert_to_json_value(self.error_message),
            "datasink": convert_to_json_value(self.datasink),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "OpenDatasinkJobDto | MessageParsingError":
        return parse_as_OpenDatasinkJobDto(value)


def parse_as_Union_of_ExportJobDto0OpenDatasinkJobDto_endof_(
    value: JsonValue,
) -> "Union[ExportJobDto, OpenDatasinkJobDto] | MessageParsingError":
    parsed_option_0 = parse_as_ExportJobDto(value)
    if not isinstance(parsed_option_0, MessageParsingError):
        return parsed_option_0
    parsed_option_1 = parse_as_OpenDatasinkJobDto(value)
    if not isinstance(parsed_option_1, MessageParsingError):
        return parsed_option_1
    return MessageParsingError(
        f"Could not parse {json.dumps(value)} into Union[ExportJobDto, OpenDatasinkJobDto]"
    )


def parse_as_Tuple_of_Union_of_ExportJobDto0OpenDatasinkJobDto_endof_0_varlen__endof_(
    value: JsonValue,
) -> "Tuple[Union[ExportJobDto, OpenDatasinkJobDto], ...] | MessageParsingError":
    if not isinstance(value, (list, tuple)):
        return MessageParsingError(
            f"Could not parse Tuple[Union[ExportJobDto, OpenDatasinkJobDto], ...] from {json.dumps(value)}"
        )
    items: List[Union[ExportJobDto, OpenDatasinkJobDto]] = []
    for item in value:
        parsed = parse_as_Union_of_ExportJobDto0OpenDatasinkJobDto_endof_(item)
        if isinstance(parsed, MessageParsingError):
            return parsed
        items.append(parsed)
    return tuple(items)


def parse_as_Tuple_of_LabelHeaderDto0_varlen__endof_(
    value: JsonValue,
) -> "Tuple[LabelHeaderDto, ...] | MessageParsingError":
    if not isinstance(value, (list, tuple)):
        return MessageParsingError(
            f"Could not parse Tuple[LabelHeaderDto, ...] from {json.dumps(value)}"
        )
    items: List[LabelHeaderDto] = []
    for item in value:
        parsed = parse_as_LabelHeaderDto(item)
        if isinstance(parsed, MessageParsingError):
            return parsed
        items.append(parsed)
    return tuple(items)


def parse_as_Union_of_Tuple_of_LabelHeaderDto0_varlen__endof_0None_endof_(
    value: JsonValue,
) -> "Union[Tuple[LabelHeaderDto, ...], None] | MessageParsingError":
    parsed_option_0 = parse_as_Tuple_of_LabelHeaderDto0_varlen__endof_(value)
    if not isinstance(parsed_option_0, MessageParsingError):
        return parsed_option_0
    parsed_option_1 = parse_as_None(value)
    if not isinstance(parsed_option_1, MessageParsingError):
        return parsed_option_1
    return MessageParsingError(
        f"Could not parse {json.dumps(value)} into Union[Tuple[LabelHeaderDto, ...], None]"
    )


def parse_as_Union_of_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto_endof_0_varlen__endof_0None_endof_(
    value: JsonValue,
) -> "Union[Tuple[Union[PrecomputedChunksDataSourceDto, N5DataSourceDto, SkimageDataSourceDto], ...], None] | MessageParsingError":
    parsed_option_0 = parse_as_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto_endof_0_varlen__endof_(
        value
    )
    if not isinstance(parsed_option_0, MessageParsingError):
        return parsed_option_0
    parsed_option_1 = parse_as_None(value)
    if not isinstance(parsed_option_1, MessageParsingError):
        return parsed_option_1
    return MessageParsingError(
        f"Could not parse {json.dumps(value)} into Union[Tuple[Union[PrecomputedChunksDataSourceDto, N5DataSourceDto, SkimageDataSourceDto], ...], None]"
    )


def parse_as_PixelClassificationExportAppletStateDto(
    value: JsonValue,
) -> "PixelClassificationExportAppletStateDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as PixelClassificationExportAppletStateDto"
        )
    if value.get("__class__") != "PixelClassificationExportAppletStateDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as PixelClassificationExportAppletStateDto"
        )
    tmp_jobs = parse_as_Tuple_of_Union_of_ExportJobDto0OpenDatasinkJobDto_endof_0_varlen__endof_(
        value.get("jobs")
    )
    if isinstance(tmp_jobs, MessageParsingError):
        return tmp_jobs
    tmp_populated_labels = (
        parse_as_Union_of_Tuple_of_LabelHeaderDto0_varlen__endof_0None_endof_(
            value.get("populated_labels")
        )
    )
    if isinstance(tmp_populated_labels, MessageParsingError):
        return tmp_populated_labels
    tmp_datasource_suggestions = parse_as_Union_of_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto_endof_0_varlen__endof_0None_endof_(
        value.get("datasource_suggestions")
    )
    if isinstance(tmp_datasource_suggestions, MessageParsingError):
        return tmp_datasource_suggestions
    return PixelClassificationExportAppletStateDto(
        jobs=tmp_jobs,
        populated_labels=tmp_populated_labels,
        datasource_suggestions=tmp_datasource_suggestions,
    )


@dataclass
class PixelClassificationExportAppletStateDto(DataTransferObject):
    jobs: Tuple[Union[ExportJobDto, OpenDatasinkJobDto], ...]
    populated_labels: Optional[Tuple[LabelHeaderDto, ...]]
    datasource_suggestions: Optional[Tuple[FsDataSourceDto, ...]]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "PixelClassificationExportAppletStateDto",
            "jobs": tuple(convert_to_json_value(item) for item in self.jobs),
            "populated_labels": convert_to_json_value(self.populated_labels),
            "datasource_suggestions": convert_to_json_value(
                self.datasource_suggestions
            ),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "PixelClassificationExportAppletStateDto | MessageParsingError":
        return parse_as_PixelClassificationExportAppletStateDto(value)


def parse_as_float(value: JsonValue) -> "float | MessageParsingError":
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    return MessageParsingError(f"Could not parse {json.dumps(value)} as float")


def parse_as_Literal_of__quote_x_quote_0_quote_y_quote_0_quote_z_quote__endof_(
    value: JsonValue,
) -> "Literal['x', 'y', 'z'] | MessageParsingError":
    tmp_0 = parse_as_str(value)
    if not isinstance(tmp_0, MessageParsingError) and tmp_0 == "x":
        return tmp_0
    tmp_1 = parse_as_str(value)
    if not isinstance(tmp_1, MessageParsingError) and tmp_1 == "y":
        return tmp_1
    tmp_2 = parse_as_str(value)
    if not isinstance(tmp_2, MessageParsingError) and tmp_2 == "z":
        return tmp_2
    return MessageParsingError(f"Could not parse {value} as Literal['x', 'y', 'z']")


def parse_as_Union_of_Literal_of__quote_x_quote_0_quote_y_quote_0_quote_z_quote__endof_0None_endof_(
    value: JsonValue,
) -> "Union[Literal['x', 'y', 'z'], None] | MessageParsingError":
    parsed_option_0 = (
        parse_as_Literal_of__quote_x_quote_0_quote_y_quote_0_quote_z_quote__endof_(
            value
        )
    )
    if not isinstance(parsed_option_0, MessageParsingError):
        return parsed_option_0
    parsed_option_1 = parse_as_None(value)
    if not isinstance(parsed_option_1, MessageParsingError):
        return parsed_option_1
    return MessageParsingError(
        f"Could not parse {json.dumps(value)} into Union[Literal['x', 'y', 'z'], None]"
    )


def parse_as_Literal_of__quote_GaussianSmoothing_quote_0_quote_LaplacianofGaussian_quote_0_quote_GaussianGradientMagnitude_quote_0_quote_DifferenceofGaussians_quote_0_quote_StructureTensorEigenvalues_quote_0_quote_HessianofGaussianEigenvalues_quote__endof_(
    value: JsonValue,
) -> "Literal['Gaussian Smoothing', 'Laplacian of Gaussian', 'Gaussian Gradient Magnitude', 'Difference of Gaussians', 'Structure Tensor Eigenvalues', 'Hessian of Gaussian Eigenvalues'] | MessageParsingError":
    tmp_0 = parse_as_str(value)
    if not isinstance(tmp_0, MessageParsingError) and tmp_0 == "Gaussian Smoothing":
        return tmp_0
    tmp_1 = parse_as_str(value)
    if not isinstance(tmp_1, MessageParsingError) and tmp_1 == "Laplacian of Gaussian":
        return tmp_1
    tmp_2 = parse_as_str(value)
    if (
        not isinstance(tmp_2, MessageParsingError)
        and tmp_2 == "Gaussian Gradient Magnitude"
    ):
        return tmp_2
    tmp_3 = parse_as_str(value)
    if (
        not isinstance(tmp_3, MessageParsingError)
        and tmp_3 == "Difference of Gaussians"
    ):
        return tmp_3
    tmp_4 = parse_as_str(value)
    if (
        not isinstance(tmp_4, MessageParsingError)
        and tmp_4 == "Structure Tensor Eigenvalues"
    ):
        return tmp_4
    tmp_5 = parse_as_str(value)
    if (
        not isinstance(tmp_5, MessageParsingError)
        and tmp_5 == "Hessian of Gaussian Eigenvalues"
    ):
        return tmp_5
    return MessageParsingError(
        f"Could not parse {value} as Literal['Gaussian Smoothing', 'Laplacian of Gaussian', 'Gaussian Gradient Magnitude', 'Difference of Gaussians', 'Structure Tensor Eigenvalues', 'Hessian of Gaussian Eigenvalues']"
    )


def parse_as_IlpFeatureExtractorDto(
    value: JsonValue,
) -> "IlpFeatureExtractorDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as IlpFeatureExtractorDto"
        )
    if value.get("__class__") != "IlpFeatureExtractorDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as IlpFeatureExtractorDto"
        )
    tmp_ilp_scale = parse_as_float(value.get("ilp_scale"))
    if isinstance(tmp_ilp_scale, MessageParsingError):
        return tmp_ilp_scale
    tmp_axis_2d = parse_as_Union_of_Literal_of__quote_x_quote_0_quote_y_quote_0_quote_z_quote__endof_0None_endof_(
        value.get("axis_2d")
    )
    if isinstance(tmp_axis_2d, MessageParsingError):
        return tmp_axis_2d
    tmp_class_name = parse_as_Literal_of__quote_GaussianSmoothing_quote_0_quote_LaplacianofGaussian_quote_0_quote_GaussianGradientMagnitude_quote_0_quote_DifferenceofGaussians_quote_0_quote_StructureTensorEigenvalues_quote_0_quote_HessianofGaussianEigenvalues_quote__endof_(
        value.get("class_name")
    )
    if isinstance(tmp_class_name, MessageParsingError):
        return tmp_class_name
    return IlpFeatureExtractorDto(
        ilp_scale=tmp_ilp_scale,
        axis_2d=tmp_axis_2d,
        class_name=tmp_class_name,
    )


@dataclass
class IlpFeatureExtractorDto(DataTransferObject):
    ilp_scale: float
    axis_2d: Optional[Literal["x", "y", "z"]]
    class_name: Literal[
        "Gaussian Smoothing",
        "Laplacian of Gaussian",
        "Gaussian Gradient Magnitude",
        "Difference of Gaussians",
        "Structure Tensor Eigenvalues",
        "Hessian of Gaussian Eigenvalues",
    ]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "IlpFeatureExtractorDto",
            "ilp_scale": self.ilp_scale,
            "axis_2d": convert_to_json_value(self.axis_2d),
            "class_name": self.class_name,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "IlpFeatureExtractorDto | MessageParsingError":
        return parse_as_IlpFeatureExtractorDto(value)


def parse_as_Tuple_of_IlpFeatureExtractorDto0_varlen__endof_(
    value: JsonValue,
) -> "Tuple[IlpFeatureExtractorDto, ...] | MessageParsingError":
    if not isinstance(value, (list, tuple)):
        return MessageParsingError(
            f"Could not parse Tuple[IlpFeatureExtractorDto, ...] from {json.dumps(value)}"
        )
    items: List[IlpFeatureExtractorDto] = []
    for item in value:
        parsed = parse_as_IlpFeatureExtractorDto(item)
        if isinstance(parsed, MessageParsingError):
            return parsed
        items.append(parsed)
    return tuple(items)


def parse_as_FeatureSelectionAppletStateDto(
    value: JsonValue,
) -> "FeatureSelectionAppletStateDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as FeatureSelectionAppletStateDto"
        )
    if value.get("__class__") != "FeatureSelectionAppletStateDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as FeatureSelectionAppletStateDto"
        )
    tmp_feature_extractors = parse_as_Tuple_of_IlpFeatureExtractorDto0_varlen__endof_(
        value.get("feature_extractors")
    )
    if isinstance(tmp_feature_extractors, MessageParsingError):
        return tmp_feature_extractors
    return FeatureSelectionAppletStateDto(
        feature_extractors=tmp_feature_extractors,
    )


@dataclass
class FeatureSelectionAppletStateDto(DataTransferObject):
    feature_extractors: Tuple[IlpFeatureExtractorDto, ...]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "FeatureSelectionAppletStateDto",
            "feature_extractors": tuple(
                item.to_json_value() for item in self.feature_extractors
            ),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "FeatureSelectionAppletStateDto | MessageParsingError":
        return parse_as_FeatureSelectionAppletStateDto(value)


def parse_as_AddFeatureExtractorsParamsDto(
    value: JsonValue,
) -> "AddFeatureExtractorsParamsDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as AddFeatureExtractorsParamsDto"
        )
    if value.get("__class__") != "AddFeatureExtractorsParamsDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as AddFeatureExtractorsParamsDto"
        )
    tmp_feature_extractors = parse_as_Tuple_of_IlpFeatureExtractorDto0_varlen__endof_(
        value.get("feature_extractors")
    )
    if isinstance(tmp_feature_extractors, MessageParsingError):
        return tmp_feature_extractors
    return AddFeatureExtractorsParamsDto(
        feature_extractors=tmp_feature_extractors,
    )


@dataclass
class AddFeatureExtractorsParamsDto(DataTransferObject):
    feature_extractors: Tuple[IlpFeatureExtractorDto, ...]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "AddFeatureExtractorsParamsDto",
            "feature_extractors": tuple(
                item.to_json_value() for item in self.feature_extractors
            ),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "AddFeatureExtractorsParamsDto | MessageParsingError":
        return parse_as_AddFeatureExtractorsParamsDto(value)


def parse_as_RemoveFeatureExtractorsParamsDto(
    value: JsonValue,
) -> "RemoveFeatureExtractorsParamsDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as RemoveFeatureExtractorsParamsDto"
        )
    if value.get("__class__") != "RemoveFeatureExtractorsParamsDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as RemoveFeatureExtractorsParamsDto"
        )
    tmp_feature_extractors = parse_as_Tuple_of_IlpFeatureExtractorDto0_varlen__endof_(
        value.get("feature_extractors")
    )
    if isinstance(tmp_feature_extractors, MessageParsingError):
        return tmp_feature_extractors
    return RemoveFeatureExtractorsParamsDto(
        feature_extractors=tmp_feature_extractors,
    )


@dataclass
class RemoveFeatureExtractorsParamsDto(DataTransferObject):
    feature_extractors: Tuple[IlpFeatureExtractorDto, ...]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "RemoveFeatureExtractorsParamsDto",
            "feature_extractors": tuple(
                item.to_json_value() for item in self.feature_extractors
            ),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "RemoveFeatureExtractorsParamsDto | MessageParsingError":
        return parse_as_RemoveFeatureExtractorsParamsDto(value)


def parse_as_Literal_of__quote_BOOT_FAIL_quote_0_quote_CANCELLED_quote_0_quote_COMPLETED_quote_0_quote_DEADLINE_quote_0_quote_FAILED_quote_0_quote_NODE_FAIL_quote_0_quote_OUT_OF_MEMORY_quote_0_quote_PENDING_quote_0_quote_PREEMPTED_quote_0_quote_RUNNING_quote_0_quote_REQUEUED_quote_0_quote_RESIZING_quote_0_quote_REVOKED_quote_0_quote_SUSPENDED_quote_0_quote_TIMEOUT_quote__endof_(
    value: JsonValue,
) -> "Literal['BOOT_FAIL', 'CANCELLED', 'COMPLETED', 'DEADLINE', 'FAILED', 'NODE_FAIL', 'OUT_OF_MEMORY', 'PENDING', 'PREEMPTED', 'RUNNING', 'REQUEUED', 'RESIZING', 'REVOKED', 'SUSPENDED', 'TIMEOUT'] | MessageParsingError":
    tmp_0 = parse_as_str(value)
    if not isinstance(tmp_0, MessageParsingError) and tmp_0 == "BOOT_FAIL":
        return tmp_0
    tmp_1 = parse_as_str(value)
    if not isinstance(tmp_1, MessageParsingError) and tmp_1 == "CANCELLED":
        return tmp_1
    tmp_2 = parse_as_str(value)
    if not isinstance(tmp_2, MessageParsingError) and tmp_2 == "COMPLETED":
        return tmp_2
    tmp_3 = parse_as_str(value)
    if not isinstance(tmp_3, MessageParsingError) and tmp_3 == "DEADLINE":
        return tmp_3
    tmp_4 = parse_as_str(value)
    if not isinstance(tmp_4, MessageParsingError) and tmp_4 == "FAILED":
        return tmp_4
    tmp_5 = parse_as_str(value)
    if not isinstance(tmp_5, MessageParsingError) and tmp_5 == "NODE_FAIL":
        return tmp_5
    tmp_6 = parse_as_str(value)
    if not isinstance(tmp_6, MessageParsingError) and tmp_6 == "OUT_OF_MEMORY":
        return tmp_6
    tmp_7 = parse_as_str(value)
    if not isinstance(tmp_7, MessageParsingError) and tmp_7 == "PENDING":
        return tmp_7
    tmp_8 = parse_as_str(value)
    if not isinstance(tmp_8, MessageParsingError) and tmp_8 == "PREEMPTED":
        return tmp_8
    tmp_9 = parse_as_str(value)
    if not isinstance(tmp_9, MessageParsingError) and tmp_9 == "RUNNING":
        return tmp_9
    tmp_10 = parse_as_str(value)
    if not isinstance(tmp_10, MessageParsingError) and tmp_10 == "REQUEUED":
        return tmp_10
    tmp_11 = parse_as_str(value)
    if not isinstance(tmp_11, MessageParsingError) and tmp_11 == "RESIZING":
        return tmp_11
    tmp_12 = parse_as_str(value)
    if not isinstance(tmp_12, MessageParsingError) and tmp_12 == "REVOKED":
        return tmp_12
    tmp_13 = parse_as_str(value)
    if not isinstance(tmp_13, MessageParsingError) and tmp_13 == "SUSPENDED":
        return tmp_13
    tmp_14 = parse_as_str(value)
    if not isinstance(tmp_14, MessageParsingError) and tmp_14 == "TIMEOUT":
        return tmp_14
    return MessageParsingError(
        f"Could not parse {value} as Literal['BOOT_FAIL', 'CANCELLED', 'COMPLETED', 'DEADLINE', 'FAILED', 'NODE_FAIL', 'OUT_OF_MEMORY', 'PENDING', 'PREEMPTED', 'RUNNING', 'REQUEUED', 'RESIZING', 'REVOKED', 'SUSPENDED', 'TIMEOUT']"
    )


def parse_as_ComputeSessionDto(
    value: JsonValue,
) -> "ComputeSessionDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as ComputeSessionDto"
        )
    if value.get("__class__") != "ComputeSessionDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as ComputeSessionDto"
        )
    tmp_start_time_utc_sec = parse_as_Union_of_int0None_endof_(
        value.get("start_time_utc_sec")
    )
    if isinstance(tmp_start_time_utc_sec, MessageParsingError):
        return tmp_start_time_utc_sec
    tmp_time_elapsed_sec = parse_as_int(value.get("time_elapsed_sec"))
    if isinstance(tmp_time_elapsed_sec, MessageParsingError):
        return tmp_time_elapsed_sec
    tmp_time_limit_minutes = parse_as_int(value.get("time_limit_minutes"))
    if isinstance(tmp_time_limit_minutes, MessageParsingError):
        return tmp_time_limit_minutes
    tmp_num_nodes = parse_as_int(value.get("num_nodes"))
    if isinstance(tmp_num_nodes, MessageParsingError):
        return tmp_num_nodes
    tmp_compute_session_id = parse_as_str(value.get("compute_session_id"))
    if isinstance(tmp_compute_session_id, MessageParsingError):
        return tmp_compute_session_id
    tmp_state = parse_as_Literal_of__quote_BOOT_FAIL_quote_0_quote_CANCELLED_quote_0_quote_COMPLETED_quote_0_quote_DEADLINE_quote_0_quote_FAILED_quote_0_quote_NODE_FAIL_quote_0_quote_OUT_OF_MEMORY_quote_0_quote_PENDING_quote_0_quote_PREEMPTED_quote_0_quote_RUNNING_quote_0_quote_REQUEUED_quote_0_quote_RESIZING_quote_0_quote_REVOKED_quote_0_quote_SUSPENDED_quote_0_quote_TIMEOUT_quote__endof_(
        value.get("state")
    )
    if isinstance(tmp_state, MessageParsingError):
        return tmp_state
    return ComputeSessionDto(
        start_time_utc_sec=tmp_start_time_utc_sec,
        time_elapsed_sec=tmp_time_elapsed_sec,
        time_limit_minutes=tmp_time_limit_minutes,
        num_nodes=tmp_num_nodes,
        compute_session_id=tmp_compute_session_id,
        state=tmp_state,
    )


@dataclass
class ComputeSessionDto(DataTransferObject):
    start_time_utc_sec: Optional[int]
    time_elapsed_sec: int
    time_limit_minutes: int
    num_nodes: int
    compute_session_id: str
    state: Literal[
        "BOOT_FAIL",
        "CANCELLED",
        "COMPLETED",
        "DEADLINE",
        "FAILED",
        "NODE_FAIL",
        "OUT_OF_MEMORY",
        "PENDING",
        "PREEMPTED",
        "RUNNING",
        "REQUEUED",
        "RESIZING",
        "REVOKED",
        "SUSPENDED",
        "TIMEOUT",
    ]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "ComputeSessionDto",
            "start_time_utc_sec": convert_to_json_value(self.start_time_utc_sec),
            "time_elapsed_sec": self.time_elapsed_sec,
            "time_limit_minutes": self.time_limit_minutes,
            "num_nodes": self.num_nodes,
            "compute_session_id": self.compute_session_id,
            "state": self.state,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "ComputeSessionDto | MessageParsingError":
        return parse_as_ComputeSessionDto(value)


def parse_as_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
    value: JsonValue,
) -> "Literal['LOCAL', 'CSCS', 'JUSUF'] | MessageParsingError":
    tmp_0 = parse_as_str(value)
    if not isinstance(tmp_0, MessageParsingError) and tmp_0 == "LOCAL":
        return tmp_0
    tmp_1 = parse_as_str(value)
    if not isinstance(tmp_1, MessageParsingError) and tmp_1 == "CSCS":
        return tmp_1
    tmp_2 = parse_as_str(value)
    if not isinstance(tmp_2, MessageParsingError) and tmp_2 == "JUSUF":
        return tmp_2
    return MessageParsingError(
        f"Could not parse {value} as Literal['LOCAL', 'CSCS', 'JUSUF']"
    )


def parse_as_bool(value: JsonValue) -> "bool | MessageParsingError":
    if isinstance(value, bool):
        return value

    return MessageParsingError(f"Could not parse {json.dumps(value)} as bool")


def parse_as_ComputeSessionStatusDto(
    value: JsonValue,
) -> "ComputeSessionStatusDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as ComputeSessionStatusDto"
        )
    if value.get("__class__") != "ComputeSessionStatusDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as ComputeSessionStatusDto"
        )
    tmp_compute_session = parse_as_ComputeSessionDto(value.get("compute_session"))
    if isinstance(tmp_compute_session, MessageParsingError):
        return tmp_compute_session
    tmp_hpc_site = parse_as_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
        value.get("hpc_site")
    )
    if isinstance(tmp_hpc_site, MessageParsingError):
        return tmp_hpc_site
    tmp_session_url = parse_as_UrlDto(value.get("session_url"))
    if isinstance(tmp_session_url, MessageParsingError):
        return tmp_session_url
    tmp_connected = parse_as_bool(value.get("connected"))
    if isinstance(tmp_connected, MessageParsingError):
        return tmp_connected
    return ComputeSessionStatusDto(
        compute_session=tmp_compute_session,
        hpc_site=tmp_hpc_site,
        session_url=tmp_session_url,
        connected=tmp_connected,
    )


@dataclass
class ComputeSessionStatusDto(DataTransferObject):
    compute_session: ComputeSessionDto
    hpc_site: Literal["LOCAL", "CSCS", "JUSUF"]
    session_url: UrlDto
    connected: bool

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "ComputeSessionStatusDto",
            "compute_session": self.compute_session.to_json_value(),
            "hpc_site": self.hpc_site,
            "session_url": self.session_url.to_json_value(),
            "connected": self.connected,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "ComputeSessionStatusDto | MessageParsingError":
        return parse_as_ComputeSessionStatusDto(value)


def parse_as_CreateComputeSessionParamsDto(
    value: JsonValue,
) -> "CreateComputeSessionParamsDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as CreateComputeSessionParamsDto"
        )
    if value.get("__class__") != "CreateComputeSessionParamsDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as CreateComputeSessionParamsDto"
        )
    tmp_session_duration_minutes = parse_as_int(value.get("session_duration_minutes"))
    if isinstance(tmp_session_duration_minutes, MessageParsingError):
        return tmp_session_duration_minutes
    tmp_hpc_site = parse_as_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
        value.get("hpc_site")
    )
    if isinstance(tmp_hpc_site, MessageParsingError):
        return tmp_hpc_site
    return CreateComputeSessionParamsDto(
        session_duration_minutes=tmp_session_duration_minutes,
        hpc_site=tmp_hpc_site,
    )


@dataclass
class CreateComputeSessionParamsDto(DataTransferObject):
    session_duration_minutes: int
    hpc_site: Literal["LOCAL", "CSCS", "JUSUF"]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "CreateComputeSessionParamsDto",
            "session_duration_minutes": self.session_duration_minutes,
            "hpc_site": self.hpc_site,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "CreateComputeSessionParamsDto | MessageParsingError":
        return parse_as_CreateComputeSessionParamsDto(value)


def parse_as_GetComputeSessionStatusParamsDto(
    value: JsonValue,
) -> "GetComputeSessionStatusParamsDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as GetComputeSessionStatusParamsDto"
        )
    if value.get("__class__") != "GetComputeSessionStatusParamsDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as GetComputeSessionStatusParamsDto"
        )
    tmp_compute_session_id = parse_as_str(value.get("compute_session_id"))
    if isinstance(tmp_compute_session_id, MessageParsingError):
        return tmp_compute_session_id
    tmp_hpc_site = parse_as_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
        value.get("hpc_site")
    )
    if isinstance(tmp_hpc_site, MessageParsingError):
        return tmp_hpc_site
    return GetComputeSessionStatusParamsDto(
        compute_session_id=tmp_compute_session_id,
        hpc_site=tmp_hpc_site,
    )


@dataclass
class GetComputeSessionStatusParamsDto(DataTransferObject):
    compute_session_id: str
    hpc_site: Literal["LOCAL", "CSCS", "JUSUF"]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "GetComputeSessionStatusParamsDto",
            "compute_session_id": self.compute_session_id,
            "hpc_site": self.hpc_site,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "GetComputeSessionStatusParamsDto | MessageParsingError":
        return parse_as_GetComputeSessionStatusParamsDto(value)


def parse_as_CloseComputeSessionParamsDto(
    value: JsonValue,
) -> "CloseComputeSessionParamsDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as CloseComputeSessionParamsDto"
        )
    if value.get("__class__") != "CloseComputeSessionParamsDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as CloseComputeSessionParamsDto"
        )
    tmp_compute_session_id = parse_as_str(value.get("compute_session_id"))
    if isinstance(tmp_compute_session_id, MessageParsingError):
        return tmp_compute_session_id
    tmp_hpc_site = parse_as_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
        value.get("hpc_site")
    )
    if isinstance(tmp_hpc_site, MessageParsingError):
        return tmp_hpc_site
    return CloseComputeSessionParamsDto(
        compute_session_id=tmp_compute_session_id,
        hpc_site=tmp_hpc_site,
    )


@dataclass
class CloseComputeSessionParamsDto(DataTransferObject):
    compute_session_id: str
    hpc_site: Literal["LOCAL", "CSCS", "JUSUF"]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "CloseComputeSessionParamsDto",
            "compute_session_id": self.compute_session_id,
            "hpc_site": self.hpc_site,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "CloseComputeSessionParamsDto | MessageParsingError":
        return parse_as_CloseComputeSessionParamsDto(value)


def parse_as_CloseComputeSessionResponseDto(
    value: JsonValue,
) -> "CloseComputeSessionResponseDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as CloseComputeSessionResponseDto"
        )
    if value.get("__class__") != "CloseComputeSessionResponseDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as CloseComputeSessionResponseDto"
        )
    tmp_compute_session_id = parse_as_str(value.get("compute_session_id"))
    if isinstance(tmp_compute_session_id, MessageParsingError):
        return tmp_compute_session_id
    return CloseComputeSessionResponseDto(
        compute_session_id=tmp_compute_session_id,
    )


@dataclass
class CloseComputeSessionResponseDto(DataTransferObject):
    compute_session_id: str

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "CloseComputeSessionResponseDto",
            "compute_session_id": self.compute_session_id,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "CloseComputeSessionResponseDto | MessageParsingError":
        return parse_as_CloseComputeSessionResponseDto(value)


def parse_as_ListComputeSessionsParamsDto(
    value: JsonValue,
) -> "ListComputeSessionsParamsDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as ListComputeSessionsParamsDto"
        )
    if value.get("__class__") != "ListComputeSessionsParamsDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as ListComputeSessionsParamsDto"
        )
    tmp_hpc_site = parse_as_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
        value.get("hpc_site")
    )
    if isinstance(tmp_hpc_site, MessageParsingError):
        return tmp_hpc_site
    return ListComputeSessionsParamsDto(
        hpc_site=tmp_hpc_site,
    )


@dataclass
class ListComputeSessionsParamsDto(DataTransferObject):
    hpc_site: Literal["LOCAL", "CSCS", "JUSUF"]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "ListComputeSessionsParamsDto",
            "hpc_site": self.hpc_site,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "ListComputeSessionsParamsDto | MessageParsingError":
        return parse_as_ListComputeSessionsParamsDto(value)


def parse_as_Tuple_of_ComputeSessionStatusDto0_varlen__endof_(
    value: JsonValue,
) -> "Tuple[ComputeSessionStatusDto, ...] | MessageParsingError":
    if not isinstance(value, (list, tuple)):
        return MessageParsingError(
            f"Could not parse Tuple[ComputeSessionStatusDto, ...] from {json.dumps(value)}"
        )
    items: List[ComputeSessionStatusDto] = []
    for item in value:
        parsed = parse_as_ComputeSessionStatusDto(item)
        if isinstance(parsed, MessageParsingError):
            return parsed
        items.append(parsed)
    return tuple(items)


def parse_as_ListComputeSessionsResponseDto(
    value: JsonValue,
) -> "ListComputeSessionsResponseDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as ListComputeSessionsResponseDto"
        )
    if value.get("__class__") != "ListComputeSessionsResponseDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as ListComputeSessionsResponseDto"
        )
    tmp_compute_sessions_stati = (
        parse_as_Tuple_of_ComputeSessionStatusDto0_varlen__endof_(
            value.get("compute_sessions_stati")
        )
    )
    if isinstance(tmp_compute_sessions_stati, MessageParsingError):
        return tmp_compute_sessions_stati
    return ListComputeSessionsResponseDto(
        compute_sessions_stati=tmp_compute_sessions_stati,
    )


@dataclass
class ListComputeSessionsResponseDto(DataTransferObject):
    compute_sessions_stati: Tuple[ComputeSessionStatusDto, ...]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "ListComputeSessionsResponseDto",
            "compute_sessions_stati": tuple(
                item.to_json_value() for item in self.compute_sessions_stati
            ),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "ListComputeSessionsResponseDto | MessageParsingError":
        return parse_as_ListComputeSessionsResponseDto(value)


def parse_as_Tuple_of_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_0_varlen__endof_(
    value: JsonValue,
) -> "Tuple[Literal['LOCAL', 'CSCS', 'JUSUF'], ...] | MessageParsingError":
    if not isinstance(value, (list, tuple)):
        return MessageParsingError(
            f"Could not parse Tuple[Literal['LOCAL', 'CSCS', 'JUSUF'], ...] from {json.dumps(value)}"
        )
    items: List[Literal["LOCAL", "CSCS", "JUSUF"]] = []
    for item in value:
        parsed = parse_as_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
            item
        )
        if isinstance(parsed, MessageParsingError):
            return parsed
        items.append(parsed)
    return tuple(items)


def parse_as_GetAvailableHpcSitesResponseDto(
    value: JsonValue,
) -> "GetAvailableHpcSitesResponseDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as GetAvailableHpcSitesResponseDto"
        )
    if value.get("__class__") != "GetAvailableHpcSitesResponseDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as GetAvailableHpcSitesResponseDto"
        )
    tmp_available_sites = parse_as_Tuple_of_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_0_varlen__endof_(
        value.get("available_sites")
    )
    if isinstance(tmp_available_sites, MessageParsingError):
        return tmp_available_sites
    return GetAvailableHpcSitesResponseDto(
        available_sites=tmp_available_sites,
    )


@dataclass
class GetAvailableHpcSitesResponseDto(DataTransferObject):
    available_sites: Tuple[Literal["LOCAL", "CSCS", "JUSUF"], ...]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "GetAvailableHpcSitesResponseDto",
            "available_sites": tuple(item for item in self.available_sites),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "GetAvailableHpcSitesResponseDto | MessageParsingError":
        return parse_as_GetAvailableHpcSitesResponseDto(value)


def parse_as_CheckLoginResultDto(
    value: JsonValue,
) -> "CheckLoginResultDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as CheckLoginResultDto"
        )
    if value.get("__class__") != "CheckLoginResultDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as CheckLoginResultDto"
        )
    tmp_logged_in = parse_as_bool(value.get("logged_in"))
    if isinstance(tmp_logged_in, MessageParsingError):
        return tmp_logged_in
    return CheckLoginResultDto(
        logged_in=tmp_logged_in,
    )


@dataclass
class CheckLoginResultDto(DataTransferObject):
    logged_in: bool

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "CheckLoginResultDto",
            "logged_in": self.logged_in,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "CheckLoginResultDto | MessageParsingError":
        return parse_as_CheckLoginResultDto(value)


def parse_as_StartPixelProbabilitiesExportJobParamsDto(
    value: JsonValue,
) -> "StartPixelProbabilitiesExportJobParamsDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as StartPixelProbabilitiesExportJobParamsDto"
        )
    if value.get("__class__") != "StartPixelProbabilitiesExportJobParamsDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as StartPixelProbabilitiesExportJobParamsDto"
        )
    tmp_datasource = parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto_endof_(
        value.get("datasource")
    )
    if isinstance(tmp_datasource, MessageParsingError):
        return tmp_datasource
    tmp_datasink = parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto_endof_(
        value.get("datasink")
    )
    if isinstance(tmp_datasink, MessageParsingError):
        return tmp_datasink
    return StartPixelProbabilitiesExportJobParamsDto(
        datasource=tmp_datasource,
        datasink=tmp_datasink,
    )


@dataclass
class StartPixelProbabilitiesExportJobParamsDto(DataTransferObject):
    datasource: FsDataSourceDto
    datasink: DataSinkDto

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "StartPixelProbabilitiesExportJobParamsDto",
            "datasource": convert_to_json_value(self.datasource),
            "datasink": convert_to_json_value(self.datasink),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "StartPixelProbabilitiesExportJobParamsDto | MessageParsingError":
        return parse_as_StartPixelProbabilitiesExportJobParamsDto(value)


def parse_as_StartSimpleSegmentationExportJobParamsDto(
    value: JsonValue,
) -> "StartSimpleSegmentationExportJobParamsDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as StartSimpleSegmentationExportJobParamsDto"
        )
    if value.get("__class__") != "StartSimpleSegmentationExportJobParamsDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as StartSimpleSegmentationExportJobParamsDto"
        )
    tmp_datasource = parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto_endof_(
        value.get("datasource")
    )
    if isinstance(tmp_datasource, MessageParsingError):
        return tmp_datasource
    tmp_datasink = parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto_endof_(
        value.get("datasink")
    )
    if isinstance(tmp_datasink, MessageParsingError):
        return tmp_datasink
    tmp_label_header = parse_as_LabelHeaderDto(value.get("label_header"))
    if isinstance(tmp_label_header, MessageParsingError):
        return tmp_label_header
    return StartSimpleSegmentationExportJobParamsDto(
        datasource=tmp_datasource,
        datasink=tmp_datasink,
        label_header=tmp_label_header,
    )


@dataclass
class StartSimpleSegmentationExportJobParamsDto(DataTransferObject):
    datasource: FsDataSourceDto
    datasink: DataSinkDto
    label_header: LabelHeaderDto

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "StartSimpleSegmentationExportJobParamsDto",
            "datasource": convert_to_json_value(self.datasource),
            "datasink": convert_to_json_value(self.datasink),
            "label_header": self.label_header.to_json_value(),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "StartSimpleSegmentationExportJobParamsDto | MessageParsingError":
        return parse_as_StartSimpleSegmentationExportJobParamsDto(value)


def parse_as_Union_of_HttpFsDto0BucketFSDto_endof_(
    value: JsonValue,
) -> "Union[HttpFsDto, BucketFSDto] | MessageParsingError":
    parsed_option_0 = parse_as_HttpFsDto(value)
    if not isinstance(parsed_option_0, MessageParsingError):
        return parsed_option_0
    parsed_option_1 = parse_as_BucketFSDto(value)
    if not isinstance(parsed_option_1, MessageParsingError):
        return parsed_option_1
    return MessageParsingError(
        f"Could not parse {json.dumps(value)} into Union[HttpFsDto, BucketFSDto]"
    )


def parse_as_LoadProjectParamsDto(
    value: JsonValue,
) -> "LoadProjectParamsDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as LoadProjectParamsDto"
        )
    if value.get("__class__") != "LoadProjectParamsDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as LoadProjectParamsDto"
        )
    tmp_fs = parse_as_Union_of_HttpFsDto0BucketFSDto_endof_(value.get("fs"))
    if isinstance(tmp_fs, MessageParsingError):
        return tmp_fs
    tmp_project_file_path = parse_as_str(value.get("project_file_path"))
    if isinstance(tmp_project_file_path, MessageParsingError):
        return tmp_project_file_path
    return LoadProjectParamsDto(
        fs=tmp_fs,
        project_file_path=tmp_project_file_path,
    )


@dataclass
class LoadProjectParamsDto(DataTransferObject):
    fs: Union[HttpFsDto, BucketFSDto]
    project_file_path: str

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "LoadProjectParamsDto",
            "fs": convert_to_json_value(self.fs),
            "project_file_path": self.project_file_path,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "LoadProjectParamsDto | MessageParsingError":
        return parse_as_LoadProjectParamsDto(value)


def parse_as_SaveProjectParamsDto(
    value: JsonValue,
) -> "SaveProjectParamsDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as SaveProjectParamsDto"
        )
    if value.get("__class__") != "SaveProjectParamsDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as SaveProjectParamsDto"
        )
    tmp_fs = parse_as_Union_of_HttpFsDto0BucketFSDto_endof_(value.get("fs"))
    if isinstance(tmp_fs, MessageParsingError):
        return tmp_fs
    tmp_project_file_path = parse_as_str(value.get("project_file_path"))
    if isinstance(tmp_project_file_path, MessageParsingError):
        return tmp_project_file_path
    return SaveProjectParamsDto(
        fs=tmp_fs,
        project_file_path=tmp_project_file_path,
    )


@dataclass
class SaveProjectParamsDto(DataTransferObject):
    fs: Union[HttpFsDto, BucketFSDto]
    project_file_path: str

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "SaveProjectParamsDto",
            "fs": convert_to_json_value(self.fs),
            "project_file_path": self.project_file_path,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "SaveProjectParamsDto | MessageParsingError":
        return parse_as_SaveProjectParamsDto(value)


def parse_as_GetDatasourcesFromUrlParamsDto(
    value: JsonValue,
) -> "GetDatasourcesFromUrlParamsDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as GetDatasourcesFromUrlParamsDto"
        )
    if value.get("__class__") != "GetDatasourcesFromUrlParamsDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as GetDatasourcesFromUrlParamsDto"
        )
    tmp_url = parse_as_UrlDto(value.get("url"))
    if isinstance(tmp_url, MessageParsingError):
        return tmp_url
    return GetDatasourcesFromUrlParamsDto(
        url=tmp_url,
    )


@dataclass
class GetDatasourcesFromUrlParamsDto(DataTransferObject):
    url: UrlDto

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "GetDatasourcesFromUrlParamsDto",
            "url": self.url.to_json_value(),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "GetDatasourcesFromUrlParamsDto | MessageParsingError":
        return parse_as_GetDatasourcesFromUrlParamsDto(value)


def parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto_endof_0_varlen__endof_0None_endof_(
    value: JsonValue,
) -> "Union[PrecomputedChunksDataSourceDto, N5DataSourceDto, SkimageDataSourceDto, Tuple[Union[PrecomputedChunksDataSourceDto, N5DataSourceDto, SkimageDataSourceDto], ...], None] | MessageParsingError":
    parsed_option_0 = parse_as_PrecomputedChunksDataSourceDto(value)
    if not isinstance(parsed_option_0, MessageParsingError):
        return parsed_option_0
    parsed_option_1 = parse_as_N5DataSourceDto(value)
    if not isinstance(parsed_option_1, MessageParsingError):
        return parsed_option_1
    parsed_option_2 = parse_as_SkimageDataSourceDto(value)
    if not isinstance(parsed_option_2, MessageParsingError):
        return parsed_option_2
    parsed_option_3 = parse_as_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto_endof_0_varlen__endof_(
        value
    )
    if not isinstance(parsed_option_3, MessageParsingError):
        return parsed_option_3
    parsed_option_4 = parse_as_None(value)
    if not isinstance(parsed_option_4, MessageParsingError):
        return parsed_option_4
    return MessageParsingError(
        f"Could not parse {json.dumps(value)} into Union[PrecomputedChunksDataSourceDto, N5DataSourceDto, SkimageDataSourceDto, Tuple[Union[PrecomputedChunksDataSourceDto, N5DataSourceDto, SkimageDataSourceDto], ...], None]"
    )


def parse_as_GetDatasourcesFromUrlResponseDto(
    value: JsonValue,
) -> "GetDatasourcesFromUrlResponseDto | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as GetDatasourcesFromUrlResponseDto"
        )
    if value.get("__class__") != "GetDatasourcesFromUrlResponseDto":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as GetDatasourcesFromUrlResponseDto"
        )
    tmp_datasources = parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto_endof_0_varlen__endof_0None_endof_(
        value.get("datasources")
    )
    if isinstance(tmp_datasources, MessageParsingError):
        return tmp_datasources
    return GetDatasourcesFromUrlResponseDto(
        datasources=tmp_datasources,
    )


@dataclass
class GetDatasourcesFromUrlResponseDto(DataTransferObject):
    datasources: Union[FsDataSourceDto, Tuple[FsDataSourceDto, ...], None]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "GetDatasourcesFromUrlResponseDto",
            "datasources": convert_to_json_value(self.datasources),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "GetDatasourcesFromUrlResponseDto | MessageParsingError":
        return parse_as_GetDatasourcesFromUrlResponseDto(value)


def parse_as_CheckDatasourceCompatibilityParams(
    value: JsonValue,
) -> "CheckDatasourceCompatibilityParams | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as CheckDatasourceCompatibilityParams"
        )
    if value.get("__class__") != "CheckDatasourceCompatibilityParams":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as CheckDatasourceCompatibilityParams"
        )
    tmp_datasources = parse_as_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto_endof_0_varlen__endof_(
        value.get("datasources")
    )
    if isinstance(tmp_datasources, MessageParsingError):
        return tmp_datasources
    return CheckDatasourceCompatibilityParams(
        datasources=tmp_datasources,
    )


@dataclass
class CheckDatasourceCompatibilityParams(DataTransferObject):
    datasources: Tuple[FsDataSourceDto, ...]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "CheckDatasourceCompatibilityParams",
            "datasources": tuple(
                convert_to_json_value(item) for item in self.datasources
            ),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "CheckDatasourceCompatibilityParams | MessageParsingError":
        return parse_as_CheckDatasourceCompatibilityParams(value)


def parse_as_Tuple_of_bool0_varlen__endof_(
    value: JsonValue,
) -> "Tuple[bool, ...] | MessageParsingError":
    if not isinstance(value, (list, tuple)):
        return MessageParsingError(
            f"Could not parse Tuple[bool, ...] from {json.dumps(value)}"
        )
    items: List[bool] = []
    for item in value:
        parsed = parse_as_bool(item)
        if isinstance(parsed, MessageParsingError):
            return parsed
        items.append(parsed)
    return tuple(items)


def parse_as_CheckDatasourceCompatibilityResponse(
    value: JsonValue,
) -> "CheckDatasourceCompatibilityResponse | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as CheckDatasourceCompatibilityResponse"
        )
    if value.get("__class__") != "CheckDatasourceCompatibilityResponse":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as CheckDatasourceCompatibilityResponse"
        )
    tmp_compatible = parse_as_Tuple_of_bool0_varlen__endof_(value.get("compatible"))
    if isinstance(tmp_compatible, MessageParsingError):
        return tmp_compatible
    return CheckDatasourceCompatibilityResponse(
        compatible=tmp_compatible,
    )


@dataclass
class CheckDatasourceCompatibilityResponse(DataTransferObject):
    compatible: Tuple[bool, ...]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "CheckDatasourceCompatibilityResponse",
            "compatible": tuple(item for item in self.compatible),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "CheckDatasourceCompatibilityResponse | MessageParsingError":
        return parse_as_CheckDatasourceCompatibilityResponse(value)


def parse_as_ListFsDirRequest(
    value: JsonValue,
) -> "ListFsDirRequest | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as ListFsDirRequest"
        )
    if value.get("__class__") != "ListFsDirRequest":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as ListFsDirRequest"
        )
    tmp_fs = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(value.get("fs"))
    if isinstance(tmp_fs, MessageParsingError):
        return tmp_fs
    tmp_path = parse_as_str(value.get("path"))
    if isinstance(tmp_path, MessageParsingError):
        return tmp_path
    return ListFsDirRequest(
        fs=tmp_fs,
        path=tmp_path,
    )


@dataclass
class ListFsDirRequest(DataTransferObject):
    fs: FsDto
    path: str

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "ListFsDirRequest",
            "fs": convert_to_json_value(self.fs),
            "path": self.path,
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "ListFsDirRequest | MessageParsingError":
        return parse_as_ListFsDirRequest(value)


def parse_as_Tuple_of_str0_varlen__endof_(
    value: JsonValue,
) -> "Tuple[str, ...] | MessageParsingError":
    if not isinstance(value, (list, tuple)):
        return MessageParsingError(
            f"Could not parse Tuple[str, ...] from {json.dumps(value)}"
        )
    items: List[str] = []
    for item in value:
        parsed = parse_as_str(item)
        if isinstance(parsed, MessageParsingError):
            return parsed
        items.append(parsed)
    return tuple(items)


def parse_as_ListFsDirResponse(
    value: JsonValue,
) -> "ListFsDirResponse | MessageParsingError":
    from collections.abc import Mapping

    if not isinstance(value, Mapping):
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as ListFsDirResponse"
        )
    if value.get("__class__") != "ListFsDirResponse":
        return MessageParsingError(
            f"Could not parse {json.dumps(value)} as ListFsDirResponse"
        )
    tmp_files = parse_as_Tuple_of_str0_varlen__endof_(value.get("files"))
    if isinstance(tmp_files, MessageParsingError):
        return tmp_files
    tmp_directories = parse_as_Tuple_of_str0_varlen__endof_(value.get("directories"))
    if isinstance(tmp_directories, MessageParsingError):
        return tmp_directories
    return ListFsDirResponse(
        files=tmp_files,
        directories=tmp_directories,
    )


@dataclass
class ListFsDirResponse(DataTransferObject):
    files: Tuple[str, ...]
    directories: Tuple[str, ...]

    def to_json_value(self) -> JsonObject:
        return {
            "__class__": "ListFsDirResponse",
            "files": tuple(item for item in self.files),
            "directories": tuple(item for item in self.directories),
        }

    @classmethod
    def from_json_value(
        cls, value: JsonValue
    ) -> "ListFsDirResponse | MessageParsingError":
        return parse_as_ListFsDirResponse(value)
