from abc import ABC, abstractmethod
from typing import Any, Optional, Type, TypeVar

from pathlib import Path
import gzip
import bz2
import lzma
from fs.base import FS as FileSystem
import json
import numpy as np

from ndstructs.point5D import Interval5D, Shape5D, Point5D
from ndstructs.utils.json_serializable import (
    JsonValue, JsonObject, ensureJsonObject, ensureJsonInt, ensureJsonIntArray, ensureJsonStringArray, ensureJsonString
)
from webilastik.datasource import guess_axiskeys

Compressor = TypeVar("Compressor", bound="N5Compressor")

class N5Compressor(ABC):
    @classmethod
    @abstractmethod
    def get_label(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def from_json_data(cls: Type[Compressor], data: JsonValue) -> Compressor:
        data_dict = ensureJsonObject(data)
        label = ensureJsonString(data_dict.get("type"))
        if label == GzipCompressor.get_label():
            return GzipCompressor.from_json_data(data)
        if label == Bzip2Compressor.get_label():
            return Bzip2Compressor.from_json_data(data)
        if label == XzCompressor.get_label():
            return XzCompressor.from_json_data(data)
        if label == RawCompressor.get_label():
            return RawCompressor.from_json_data(data)
        raise ValueError(f"Could not interpret {json.dumps(data)} as an n5 compressor")

    @abstractmethod
    def to_json_data(self) -> JsonObject:
        return {"type": self.get_label()}

    @abstractmethod
    def compress(self, raw: bytes) -> bytes:
        pass

    @abstractmethod
    def decompress(self, compressed: bytes) -> bytes:
        pass

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.to_json_data() == other.to_json_data()


class GzipCompressor(N5Compressor):
    def __init__(self, level: int = 1):
        self.level = level

    @classmethod
    def get_label(cls) -> str:
        return "gzip"

    @classmethod
    def from_json_data(cls, data: JsonValue) -> "GzipCompressor":
        return GzipCompressor(
            level=ensureJsonInt(ensureJsonObject(data).get("level", 1))
        )

    def to_json_data(self) -> JsonObject:
        return {
            **super().to_json_data(),
            "level": self.level
        }

    def compress(self, raw: bytes) -> bytes:
        return gzip.compress(raw, compresslevel=self.level)

    def decompress(self, compressed: bytes) -> bytes:
        return gzip.decompress(compressed)


class Bzip2Compressor(N5Compressor):
    def __init__(self, blockSize: int = 9):
        self.blockSize = blockSize

    @classmethod
    def get_label(cls) -> str:
        return "bzip2"

    @classmethod
    def from_json_data(cls, data: JsonValue) -> "Bzip2Compressor":
        return Bzip2Compressor(
            blockSize=ensureJsonInt(ensureJsonObject(data).get("blockSize", 9))
        )

    def to_json_data(self) -> JsonObject:
        return {
            **super().to_json_data(),
            "blockSize": self.blockSize
        }

    def compress(self, raw: bytes) -> bytes:
        return bz2.compress(raw, self.blockSize)

    def decompress(self, compressed: bytes) -> bytes:
        return bz2.decompress(compressed)


class XzCompressor(N5Compressor):
    def __init__(self, preset: int = 6):
        self.preset = preset

    @classmethod
    def get_label(cls) -> str:
        return "xz"

    @classmethod
    def from_json_data(cls, data: JsonValue) -> "XzCompressor":
        return XzCompressor(
            preset=ensureJsonInt(ensureJsonObject(data).get("preset"))
        )

    def to_json_data(self) -> JsonObject:
        return {
            **super().to_json_data(),
            "preset": self.preset
        }

    def compress(self, raw: bytes) -> bytes:
        return lzma.compress(raw, preset=self.preset)

    def decompress(self, compressed: bytes) -> bytes:
        return lzma.decompress(compressed)


class RawCompressor(N5Compressor):
    @classmethod
    def get_label(cls) -> str:
        return "raw"

    @classmethod
    def from_json_data(cls, data: JsonValue) -> "RawCompressor":
        return RawCompressor()

    def to_json_data(self) -> JsonObject:
        return super().to_json_data()

    def compress(self, raw: bytes) -> bytes:
        return raw

    def decompress(self, compressed: bytes) -> bytes:
        return compressed

class N5DatasetAttributes:
    def __init__(
        self,
        *,
        dimensions: Shape5D,
        blockSize: Shape5D,
        c_axiskeys: str,
        dataType: "np.dtype[Any]", #FIXME
        compression: N5Compressor,
        location: Point5D = Point5D.zero(),
    ):
        """axiskeys follows ndstructs conventions (c-order), despite 'axes' in N5 datasets being F-order"""
        self.dimensions = dimensions
        self.blockSize = blockSize
        self.c_axiskeys = c_axiskeys
        self.dataType = dataType
        self.compression = compression
        self.location = location
        self.interval = self.dimensions.to_interval5d(self.location)

    def get_tile_path(self, tile: Interval5D) -> Path:
        "Gets the relative path into the n5 dataset where 'tile' should be stored"
        if not tile.is_tile(tile_shape=self.blockSize, full_interval=self.interval, clamped=True):
            raise ValueError(f"{tile} is not a tile of {json.dumps(self.to_json_data())}")
        slice_address_components = (tile.translated(-self.location).start // self.blockSize).to_tuple(self.c_axiskeys[::-1])
        return Path("/".join(str(component) for component in slice_address_components))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, N5DatasetAttributes):
            return False
        return (
            self.dimensions == other.dimensions and
            self.blockSize == other.blockSize and
            self.c_axiskeys == other.c_axiskeys and
            self.dataType == other.dataType and
            self.compression == other.compression
        )

    @classmethod
    def load(cls, path: Path, filesystem: FileSystem) -> "N5DatasetAttributes":
        with filesystem.openbin(path.joinpath("attributes.json").as_posix(), "r") as f:
            attributes_json = f.read().decode("utf8")
        raw_attributes = json.loads(attributes_json)
        return cls.from_json_data(raw_attributes)

    @classmethod
    def from_json_data(cls, data: JsonValue, location_override: Optional[Point5D] = None) -> "N5DatasetAttributes":
        raw_attributes = ensureJsonObject(data)

        dimensions = ensureJsonIntArray(raw_attributes.get("dimensions"))
        blockSize = ensureJsonIntArray(raw_attributes.get("blockSize"))
        axes = raw_attributes.get("axes")
        if axes is None:
            c_axiskeys = guess_axiskeys(dimensions)
        else:
            c_axiskeys = "".join(ensureJsonStringArray(axes)[::-1]).lower()
        location = raw_attributes.get("location")
        if location is None:
            location_5d = Point5D.zero()
        else:
            location_5d = Point5D.zero(**dict(zip(c_axiskeys, ensureJsonIntArray(location)[::-1])))

        return N5DatasetAttributes(
            blockSize=Shape5D.create(raw_shape=blockSize[::-1], axiskeys=c_axiskeys),
            dimensions=Shape5D.create(raw_shape=dimensions[::-1], axiskeys=c_axiskeys),
            dataType=np.dtype(ensureJsonString(raw_attributes.get("dataType"))).newbyteorder(">"), # type: ignore
            c_axiskeys=c_axiskeys,
            compression=N5Compressor.from_json_data(raw_attributes["compression"]),
            location=location_override or location_5d,
        )

    def to_json_data(self) -> JsonObject:
        return {
            "dimensions": self.dimensions.to_tuple(self.c_axiskeys[::-1]),
            "blockSize": self.blockSize.to_tuple(self.c_axiskeys[::-1]),
            "axes": tuple(self.c_axiskeys[::-1]),
            "dataType": str(self.dataType.name),
            "compression": self.compression.to_json_data(),
            "location": self.location.to_tuple(self.c_axiskeys[::-1])
        }
