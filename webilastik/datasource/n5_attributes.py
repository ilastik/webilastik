from abc import ABC, abstractmethod
from typing import Any

from pathlib import PurePosixPath
import gzip
import bz2
import lzma
import json
import numpy as np

from ndstructs.point5D import Interval5D, Shape5D
from webilastik.datasource import guess_axiskeys
from webilastik.serialization.json_serialization import parse_json
from webilastik.server.rpc.dto import (
    N5DatasetAttributesDto, N5Bzip2CompressorDto, N5CompressorDto, N5GzipCompressorDto, N5XzCompressorDto, N5RawCompressorDto, dtype_to_dto
)
from webilastik.filesystem import IFilesystem

class N5Compressor(ABC):
    @abstractmethod
    def to_dto(self) -> N5CompressorDto:
        pass

    @staticmethod
    def create_from_dto(dto: N5CompressorDto) -> "N5Compressor":
        if isinstance(dto, N5GzipCompressorDto):
            return GzipCompressor.from_dto(dto)
        if isinstance(dto, N5Bzip2CompressorDto):
            return Bzip2Compressor.from_dto(dto)
        if isinstance(dto, N5XzCompressorDto):
            return XzCompressor.from_dto(dto)
        return RawCompressor.from_dto(dto)

    @abstractmethod
    def compress(self, raw: bytes) -> bytes:
        pass

    @abstractmethod
    def decompress(self, compressed: bytes) -> bytes:
        pass

class GzipCompressor(N5Compressor):
    def __init__(self, level: int = 1):
        self.level = level
        super().__init__()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, GzipCompressor) and self.level == other.level

    def to_dto(self) -> N5GzipCompressorDto:
        return N5GzipCompressorDto(level=self.level)

    @staticmethod
    def from_dto(dto: N5GzipCompressorDto) -> "GzipCompressor":
        return GzipCompressor(level=dto.level)

    def compress(self, raw: bytes) -> bytes:
        return gzip.compress(raw, compresslevel=self.level)

    def decompress(self, compressed: bytes) -> bytes:
        return gzip.decompress(compressed)


class Bzip2Compressor(N5Compressor):
    def __init__(self, compressionLevel: int = 9):
        self.compressionLevel = compressionLevel
        super().__init__()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Bzip2Compressor) and self.compressionLevel == other.compressionLevel

    def to_dto(self) -> N5Bzip2CompressorDto:
        return N5Bzip2CompressorDto(blockSize=self.compressionLevel)

    @staticmethod
    def from_dto(dto: N5Bzip2CompressorDto) -> "Bzip2Compressor":
        return Bzip2Compressor(compressionLevel=dto.blockSize)

    def compress(self, raw: bytes) -> bytes:
        return bz2.compress(raw, self.compressionLevel)

    def decompress(self, compressed: bytes) -> bytes:
        return bz2.decompress(compressed)


class XzCompressor(N5Compressor):
    def __init__(self, preset: int = 6):
        self.preset = preset
        super().__init__()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, XzCompressor) and self.preset == other.preset

    def to_dto(self) -> N5XzCompressorDto:
        return N5XzCompressorDto(preset=self.preset)

    @staticmethod
    def from_dto(dto: N5XzCompressorDto) -> "XzCompressor":
        return XzCompressor(preset=dto.preset)

    def compress(self, raw: bytes) -> bytes:
        return lzma.compress(raw, preset=self.preset)

    def decompress(self, compressed: bytes) -> bytes:
        return lzma.decompress(compressed)


class RawCompressor(N5Compressor):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, RawCompressor)

    def to_dto(self) -> N5RawCompressorDto:
        return N5RawCompressorDto()

    @staticmethod
    def from_dto(dto: N5RawCompressorDto) -> "RawCompressor":
        return RawCompressor()

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
    ):
        """axiskeys follows ndstructs conventions (c-order), despite 'axes' in N5 datasets being F-order"""
        self.dimensions = dimensions
        self.blockSize = blockSize
        self.c_axiskeys = c_axiskeys
        self.dataType = dataType
        self.compression = compression
        self.interval = self.dimensions.to_interval5d()
        super().__init__()

    def get_tile_path(self, tile: Interval5D) -> PurePosixPath:
        "Gets the relative path into the n5 dataset where 'tile' should be stored"
        assert tile.is_tile(tile_shape=self.blockSize, full_interval=self.interval, clamped=True), f"Bad tile: {tile}"

        if not tile.is_tile(tile_shape=self.blockSize, full_interval=self.interval, clamped=True):
            raise ValueError(f"{tile} is not a tile of {json.dumps(self.to_dto().to_json_value())}")
        slice_address_components = (tile.translated(-self.interval.start).start // self.blockSize).to_tuple(self.c_axiskeys[::-1])
        return PurePosixPath("/".join(str(component) for component in slice_address_components))

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
    def try_load(cls, path: PurePosixPath, filesystem: IFilesystem) -> "N5DatasetAttributes | Exception":
        read_result = filesystem.read_file(path)
        if isinstance(read_result, Exception):
            return read_result
        attributes_json_result = parse_json(read_result)
        if isinstance(attributes_json_result, Exception):
            return attributes_json_result
        dto_result = N5DatasetAttributesDto.from_json_value(attributes_json_result)
        if isinstance(dto_result, Exception):
            return dto_result
        return N5DatasetAttributes.from_dto(dto_result)

    @classmethod
    def from_dto(cls, dto: N5DatasetAttributesDto) -> "N5DatasetAttributes | Exception":
        if dto.axes is None:
            c_axiskeys = guess_axiskeys(dto.dimensions)
        else:
            c_axiskeys = "".join(dto.axes[::-1]).lower()

        if len(set(len(prop) for prop in [dto.dimensions, dto.blockSize, c_axiskeys])) != 1:
            return Exception(f"Missmatched lengths of N5 attribute properties")

        return N5DatasetAttributes(
            blockSize=Shape5D.create(raw_shape=dto.blockSize[::-1], axiskeys=c_axiskeys),
            dimensions=Shape5D.create(raw_shape=dto.dimensions[::-1], axiskeys=c_axiskeys),
            dataType=np.dtype(dto.dataType).newbyteorder(">"),
            c_axiskeys=c_axiskeys,
            compression=N5Compressor.create_from_dto(dto.compression),
        )

    def to_dto(self) -> N5DatasetAttributesDto:
        return N5DatasetAttributesDto(
            dimensions=self.dimensions.to_tuple(self.c_axiskeys[::-1]),
            blockSize=self.blockSize.to_tuple(self.c_axiskeys[::-1]),
            axes=tuple(self.c_axiskeys[::-1]),
            dataType=dtype_to_dto(self.dataType),
            compression=self.compression.to_dto(),
        )
