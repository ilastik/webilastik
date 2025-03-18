from typing import Any, Optional, Tuple
from pathlib import PurePosixPath
import enum
from webilastik.filesystem import FsFileNotFoundException, IFilesystem, create_filesystem_from_message

import numpy as np
from ndstructs.point5D import Point5D, Interval5D, Shape5D
from ndstructs.array5D import Array5D

from webilastik.datasource.n5_attributes import N5Compressor, N5DatasetAttributes
from webilastik.datasource import FsDataSource
from webilastik.server.rpc.dto import Interval5DDto, N5DataSourceDto, Shape5DDto, dtype_to_dto

class N5Block(Array5D):
    class Modes(enum.IntEnum):
        DEFAULT = 0
        VARLENGTH = 1

    @classmethod
    def from_bytes(cls, data: bytes, c_axiskeys: str, dtype: "np.dtype[Any]", compression: N5Compressor, location: Point5D) -> "N5Block":
        data_bytes = np.frombuffer(data, dtype=np.uint8)

        header_types = [
            ("mode", ">u2"),  # mode (uint16 big endian, default = 0x0000, varlength = 0x0001)
            ("num_dims", ">u2"),  # number of dimensions (uint16 big endian)
        ]
        preamble = np.frombuffer(data_bytes, dtype=header_types, count=1)
        header_types.append(
              # dimension 1[,...,n] (uint32 big endian)
            ("dimensions", str(preamble["num_dims"].item()) + ">u4")
        )

        if preamble["mode"].item() == cls.Modes.VARLENGTH.value:
            # mode == varlength ? number of elements (uint32 big endian)
            header_types.append(("num_elements", ">u4"))
            raise RuntimeError("Don't know how to handle varlen N5 blocks")

        header_dtype = np.dtype(header_types)
        header_data = np.frombuffer(data_bytes, dtype=header_dtype, count=1)
        array_shape: Tuple[int, ...] = header_data["dimensions"].squeeze() #type: ignore

        compressed_buffer: "np.ndarray[Any, np.dtype[np.uint8]]" = np.frombuffer(data_bytes, offset=header_dtype.itemsize, dtype=np.uint8)
        decompressed_buffer = compression.decompress(compressed_buffer.tobytes())
        raw_array: "np.ndarray[Any, np.dtype[Any]]" = np.frombuffer(decompressed_buffer, dtype=dtype.newbyteorder(">")).reshape(array_shape, order="F")

        return cls(raw_array, axiskeys=c_axiskeys[::-1], location=location)

    def to_n5_bytes(self, axiskeys: str, compression: N5Compressor):
        # because the axistags are written in reverse order to attributes.json, bytes must be written in C order.
        data_buffer = compression.compress(self.raw(axiskeys).astype(self.dtype.newbyteorder(">")).tobytes("C"))
        tile_types = [
            ("mode", ">u2"),  # mode (uint16 big endian, default = 0x0000, varlength = 0x0001)
            ("num_dims", ">u2"),  # number of dimensions (uint16 big endian)
            ("dimensions", f"{len(axiskeys)}>u4"),  # dimension 1[,...,n] (uint32 big endian)
            ("data", f"{len(data_buffer)}u1"),
        ]
        tile: "np.ndarray[Any, Any]" = np.zeros(1, dtype=tile_types)
        tile["mode"] = self.Modes.DEFAULT.value
        tile["num_dims"] = len(axiskeys)
        tile["dimensions"] = [self.shape[k] for k in axiskeys[::-1]]
        tile["data"] = np.ndarray((len(data_buffer),), dtype=np.uint8, buffer=data_buffer)
        return tile.tobytes()


class N5DataSource(FsDataSource):
    """An FsDataSource representing an N5 dataset. "axiskeys" are, like everywhere else in ndstructs, C-ordered."""

    def __init__(
        self,
        *,
        filesystem: IFilesystem,
        path: PurePosixPath,
        interval: Interval5D,
        tile_shape: Shape5D,
        c_axiskeys_on_disk: str,
        dtype: "np.dtype[Any]",
        spatial_resolution: Optional[Tuple[int, int, int]] = None,
        compressor: N5Compressor,
    ):
        self.compressor = compressor
        super().__init__(
            c_axiskeys_on_disk=c_axiskeys_on_disk,
            filesystem=filesystem,
            path=path,
            tile_shape=tile_shape,
            interval=interval,
            dtype=dtype,
            spatial_resolution=spatial_resolution,
        )
        self.attributes = N5DatasetAttributes(
            dimensions=self.interval.shape,
            c_axiskeys=self.c_axiskeys_on_disk,
            blockSize=self.tile_shape,
            compression=self.compressor,
            dataType=self.dtype,
        )

    @classmethod
    def try_load(
        cls,
        *,
        filesystem: IFilesystem,
        path: PurePosixPath,
        spatial_resolution: Optional[Tuple[int, int, int]] = None,
    ) -> "N5DataSource | Exception":
        attributes_result = N5DatasetAttributes.try_load(filesystem=filesystem, path=path.joinpath("attributes.json"))
        if isinstance(attributes_result, Exception):
            return attributes_result

        return N5DataSource(
            filesystem=filesystem,
            path=path,
            c_axiskeys_on_disk=attributes_result.c_axiskeys,
            tile_shape=attributes_result.blockSize,
            interval=attributes_result.interval,
            dtype=attributes_result.dataType,
            spatial_resolution=spatial_resolution,
            compressor=attributes_result.compression,
        )

    @staticmethod
    def from_dto(dto: N5DataSourceDto) -> "N5DataSource | Exception":
        fs_result = create_filesystem_from_message(dto.filesystem)
        if isinstance(fs_result, Exception):
            return fs_result

        return N5DataSource(
            filesystem=fs_result,
            path=PurePosixPath(dto.path),
            dtype=np.dtype(dto.dtype),
            interval=dto.interval.to_interval5d(),
            compressor=N5Compressor.create_from_dto(dto.compressor),
            spatial_resolution=dto.spatial_resolution,
            tile_shape=dto.tile_shape.to_shape5d(),
            c_axiskeys_on_disk=dto.c_axiskeys_on_disk,
        )

    def to_dto(self) -> N5DataSourceDto:
        return N5DataSourceDto(
            url=self.url.to_dto(),
            filesystem=self.filesystem.to_dto(),
            path=self.path.as_posix(),
            interval=Interval5DDto.from_interval5d(self.interval),
            spatial_resolution=self.spatial_resolution,
            tile_shape=Shape5DDto.from_shape5d(self.tile_shape),
            dtype=dtype_to_dto(self.dtype),
            c_axiskeys_on_disk=self.c_axiskeys_on_disk,
            compressor=self.compressor.to_dto(),
        )

    def __hash__(self) -> int:
        return hash((self.filesystem.geturl(self.path), self.interval))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, N5DataSource) and
            super().__eq__(other) and
            self.filesystem.geturl(self.path) == other.filesystem.geturl(other.path)
        )

    def _get_tile(self, tile: Interval5D) -> Array5D:
        slice_address = self.path / self.attributes.get_tile_path(tile)
        read_result = self.filesystem.read_file(slice_address)
        if isinstance(read_result, FsFileNotFoundException):
            return self._allocate(interval=tile, fill_value=0)
        if isinstance(read_result, Exception):
            raise read_result #FIXME: return instead
        return N5Block.from_bytes(
            data=read_result, c_axiskeys=self.c_axiskeys_on_disk, dtype=self.dtype, compression=self.compressor, location=tile.start
        )
