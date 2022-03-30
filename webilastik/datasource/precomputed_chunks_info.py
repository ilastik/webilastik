from abc import ABC, abstractmethod
import json
from typing import Any, Literal, Optional, Tuple
from pathlib import PurePosixPath
import io

import numpy as np
import skimage.io #type: ignore

from ndstructs.utils.json_serializable import (
    JsonValue, JsonObject, ensureJsonObject, ensureJsonString, ensureJsonIntTripplet, ensureJsonArray, ensureJsonInt, ensureOptional
)
from ndstructs.point5D import Point5D, Shape5D, Interval5D
from ndstructs.array5D import Array5D

from webilastik.datasource import DataSource
from webilastik.filesystem import JsonableFilesystem

class PrecomputedChunksEncoder(ABC):
    @abstractmethod
    def decode(
        self,
        *,
        roi: Interval5D,
        dtype: np.dtype, #type: ignore
        raw_chunk: bytes
    ) -> Array5D:
        pass

    @abstractmethod
    def encode(self, data: Array5D) -> bytes:
        pass

    @abstractmethod
    def to_json_value(self) -> JsonValue:
        pass

    @classmethod
    def from_json_value(cls, data: JsonValue) -> "PrecomputedChunksEncoder":
        label = ensureJsonString(data)
        if label == "raw":
            return RawEncoder()
        if label == "jpeg" or label == "jpg":
            return JpegEncoder()
        raise ValueError(f"Bad encoding value: {label}")

class RawEncoder(PrecomputedChunksEncoder):
    def to_json_value(self) -> JsonValue:
        return "raw"

    def decode(
        self,
        *,
        roi: Interval5D,
        dtype: "np.dtype[Any]", #FIXME
        raw_chunk: bytes
    ) -> Array5D:
        # "The (...) data (...) chunk is stored directly in little-endian binary format in [x, y, z, channel] Fortran order"
        raw_tile: np.ndarray[Any, Any] = np.frombuffer( #type: ignore
            raw_chunk,
            dtype=dtype.newbyteorder("<") # type: ignore
        ).reshape(roi.shape.to_tuple("xyzc"), order="F")
        tile_5d = Array5D(raw_tile, axiskeys="xyzc", location=roi.start)
        return tile_5d

    def encode(self, data: Array5D) -> bytes:
        return data.raw("xyzc").tobytes("F") #type: ignore #FIXME

class JpegEncoder(PrecomputedChunksEncoder):
    def to_json_value(self) -> JsonValue:
        return "jpeg"

    def decode(
        self,
        *,
        roi: Interval5D,
        dtype: np.dtype, #type: ignore
        raw_chunk: bytes
    ) -> Array5D:
        # "The width and height of the JPEG image may be arbitrary (...)"
        # "the total number of pixels is equal to the product of the x, y, and z dimensions of the subvolume"
        # "(...) the 1-D array obtained by concatenating the horizontal rows of the image corresponds to the
        # flattened [x, y, z] Fortran-order (i,e. zyx C order) representation of the subvolume."

        # FIXME: check if this works with any sort of funny JPEG shapes
        # FIXME: Also, what to do if dtype is weird?
        raw_jpg: np.ndarray = skimage.io.imread(io.BytesIO(raw_chunk)) # type: ignore
        tile_5d = Array5D(raw_jpg.reshape(roi.shape.to_tuple("zyxc")), axiskeys="zyxc", location=roi.start)
        return tile_5d

    def encode(self, data: Array5D) -> bytes:
        raise NotImplementedError


class PrecomputedChunksScale:
    def __init__(
        self,
        key: PurePosixPath,
        size: Tuple[int, int, int],
        resolution: Tuple[int, int, int],
        voxel_offset: Optional[Tuple[int, int, int]],
        chunk_sizes: Tuple[Tuple[int, int, int], ...],
        encoding: PrecomputedChunksEncoder,
    ) -> None:
        self.key = PurePosixPath(key.as_posix().lstrip("/"))
        self.size = size
        self.resolution = resolution
        self.voxel_offset = (0,0,0) if voxel_offset is None else voxel_offset
        self.chunk_sizes = chunk_sizes
        self.encoding = encoding

    @classmethod
    def from_datasource(
        cls, *, datasource: DataSource, key: PurePosixPath, encoding: PrecomputedChunksEncoder
    ) -> "PrecomputedChunksScale":
        return PrecomputedChunksScale(
            key=key,
            chunk_sizes=tuple([
                (datasource.tile_shape.x, datasource.tile_shape.y, datasource.tile_shape.z)
            ]),
            size=(datasource.shape.x, datasource.shape.y, datasource.shape.z),
            resolution=datasource.spatial_resolution,
            voxel_offset=(datasource.location.x, datasource.location.y, datasource.location.z),
            encoding=encoding
        )

    def to_json_value(self) -> JsonObject:
        return {
            "key": self.key.as_posix(),
            "size": self.size,
            "resolution": self.resolution,
            "voxel_offset": self.voxel_offset,
            "chunk_sizes": self.chunk_sizes,
            "encoding": self.encoding.to_json_value(),
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "PrecomputedChunksScale":
        value_obj = ensureJsonObject(value)
        return PrecomputedChunksScale(
            key=PurePosixPath(ensureJsonString(value_obj.get("key"))),
            size=ensureJsonIntTripplet(value_obj.get("size")),
            resolution=ensureJsonIntTripplet(value_obj.get("resolution")),
            voxel_offset=ensureOptional(ensureJsonIntTripplet, value_obj.get("voxel_offset")),
            chunk_sizes=tuple([
                ensureJsonIntTripplet(v)
                for v in ensureJsonArray(value_obj.get("chunk_sizes"))
            ]),
            encoding=PrecomputedChunksEncoder.from_json_value(value_obj.get("encoding")),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PrecomputedChunksScale):
            return False
        return (
            self.key == other.key and
            self.size == other.size and
            self.resolution == other.resolution and
            self.voxel_offset == other.voxel_offset and
            self.chunk_sizes == other.chunk_sizes and
            self.encoding == other.encoding
        )

class PrecomputedChunksScale5D(PrecomputedChunksScale):
    def __init__(
        self,
        *,
        key: PurePosixPath,
        size: Tuple[int, int, int],
        resolution: Tuple[int, int, int],
        voxel_offset: Tuple[int, int, int],
        chunk_sizes: Tuple[Tuple[int, int, int], ...],
        encoding: PrecomputedChunksEncoder,
        num_channels: int,
    ):
        super().__init__(
            key=key, size=size, resolution=resolution, voxel_offset=voxel_offset, chunk_sizes=chunk_sizes, encoding=encoding
        )
        self.num_channels = num_channels
        self.shape = Shape5D(x=self.size[0], y=self.size[1], z=self.size[2], c=num_channels)
        self.location = Point5D(x=self.voxel_offset[0], y=self.voxel_offset[1], z=self.voxel_offset[2])
        self.interval = self.shape.to_interval5d(offset=self.location)
        self.chunk_sizes_5d = [Shape5D(x=cs[0], y=cs[1], z=cs[2], c=num_channels) for cs in self.chunk_sizes]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PrecomputedChunksScale5D):
            return False
        return super().__eq__(other) and self.num_channels == other.num_channels

    @classmethod
    def from_raw_scale(cls, scale: PrecomputedChunksScale, *, num_channels: int) -> "PrecomputedChunksScale5D":
        return PrecomputedChunksScale5D(
            key=scale.key,
            size=scale.size,
            resolution=scale.resolution,
            voxel_offset=scale.voxel_offset,
            chunk_sizes=scale.chunk_sizes,
            encoding=scale.encoding,
            num_channels=num_channels,
        )

    def to_json_value(self) -> JsonObject:
        return {
            **super().to_json_value(),
            "num_channels": self.num_channels,
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "PrecomputedChunksScale5D":
        value_obj = ensureJsonObject(value)
        raw_scale = PrecomputedChunksScale.from_json_value(value)
        return PrecomputedChunksScale5D.from_raw_scale(raw_scale, num_channels=ensureJsonInt(value_obj.get("num_channels")))

    def get_tile_path(self, tile: Interval5D) -> PurePosixPath:
        assert any(tile.is_tile(tile_shape=cs, full_interval=self.interval, clamped=True) for cs in self.chunk_sizes_5d), f"Bad tile: {tile}"
        return self.key / f"{tile.x[0]}-{tile.x[1]}_{tile.y[0]}-{tile.y[1]}_{tile.z[0]}-{tile.z[1]}"


class PrecomputedChunksInfo:
    def __init__(
        self,
        *,
        type_: Literal["image"],
        data_type: "np.dtype[Any]", #FIXME
        num_channels: int,
        scales: Tuple[PrecomputedChunksScale, ...],
    ):
        self.type_: Literal["image"] = type_
        self.data_type = data_type
        self.num_channels = num_channels
        self.scales = scales
        self.scales_5d = [
            PrecomputedChunksScale5D.from_raw_scale(scale, num_channels=num_channels) for scale in scales
        ]

        if self.type_ != "image":
            raise NotImplementedError(f"Don't know how to interpret type '{self.type_}'")
        if num_channels <= 0:
            raise ValueError("num_channels must be greater than 0", self.__dict__)
        if len(scales) == 0:
            raise ValueError("Must provide at least one scale", self.__dict__)

    @classmethod
    def from_datasource(
        cls,
        *,
        datasource: DataSource,
        scale_key: PurePosixPath,
        encoding: PrecomputedChunksEncoder = RawEncoder(),
        num_channels: Optional[int] = None,
        data_type: "np.dtype[Any] | None" = None, #FIXME: remove Any?
    ) -> "PrecomputedChunksInfo":
        return PrecomputedChunksInfo(
            type_="image",
            data_type=data_type or datasource.dtype,
            num_channels=num_channels or datasource.shape.c,
            scales=tuple([
                PrecomputedChunksScale.from_datasource(
                    datasource=datasource, key=scale_key, encoding=encoding
                )
            ])
        )

    def stripped(self, resolution: Tuple[int, int, int]) -> "PrecomputedChunksInfo":
        return PrecomputedChunksInfo(
            type_=self.type_,
            data_type=self.data_type, #type: ignore
            num_channels=self.num_channels,
            scales=tuple([self.get_scale_5d(resolution=resolution)])
        )

    def get_scale_5d(self, resolution: Tuple[int, int, int]) -> PrecomputedChunksScale5D:
        for scale in self.scales_5d:
            if scale.resolution == resolution:
                return scale
        raise ValueError(f"Scale with resolution {resolution} not found")

    def contains(self, scale: PrecomputedChunksScale) -> bool:
        return any(scale == s for s in self.scales)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PrecomputedChunksInfo) and
            self.type_ == other.type_ and
            self.data_type == other.data_type and #type: ignore
            self.num_channels == other.num_channels and
            self.scales == other.scales
        )

    @classmethod
    def tryLoad(cls, filesystem: JsonableFilesystem, path: PurePosixPath) ->"PrecomputedChunksInfo | Exception":
        url = filesystem.geturl(path.as_posix())
        if not filesystem.exists(path.as_posix()):
            return FileNotFoundError(f"Could not find info file at {url}")
        with filesystem.openbin(path.as_posix(), "r") as f:
            try:
                info_json = f.read().decode("utf8")
                return PrecomputedChunksInfo.from_json_value(json.loads(info_json))
            except Exception:
                return ValueError(f"Could not interpret json info file at {url}")

    @classmethod
    def from_json_value(cls, data: JsonValue):
        data_dict = ensureJsonObject(data)
        type_ = ensureJsonString(data_dict.get("type"))
        if type_ != "image":
            raise ValueError(f"Bad 'type' marker value: {type_}")
        return PrecomputedChunksInfo(
            type_=type_,
            data_type=np.dtype(ensureJsonString(data_dict.get("data_type"))), #type: ignore
            num_channels=ensureJsonInt(data_dict.get("num_channels")),
            scales=tuple(
                PrecomputedChunksScale.from_json_value(raw_scale)
                for raw_scale in ensureJsonArray(data_dict.get("scales"))
            )
        )

    def to_json_value(self) -> JsonObject:
        return {
            "@type": "neuroglancer_multiscale_volume",
            "type": self.type_,
            "data_type": str(self.data_type.name), #type: ignore
            "num_channels": self.num_channels,
            "scales": tuple(scale.to_json_value() for scale in self.scales),
        }
