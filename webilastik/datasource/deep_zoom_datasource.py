# pyright: strict

from collections import Mapping
from typing import Dict, Literal, Mapping, Tuple
from pathlib import PurePosixPath
import logging
import io
import math

import numpy as np
from PIL import Image as PilImage
from ndstructs.point5D import Point5D, Interval5D
from ndstructs.array5D import Array5D

from webilastik.datasource import FsDataSource
from webilastik.datasource.deep_zoom_image import DziImageElement, GarbledTileException
from webilastik.filesystem import FsFileNotFoundException, IFilesystem
from webilastik.server.rpc.dto import DziLevelDataSourceDto
from webilastik.filesystem import FsFileNotFoundException, IFilesystem


logger = logging.getLogger(__name__)



class DziLevelDataSource(FsDataSource):
    def __init__(
        self,
        *,
        filesystem: IFilesystem,
        xml_path: PurePosixPath,
        dzi_image: DziImageElement,
        num_channels: Literal[1, 3],
        level_index: int,
        spatial_resolution: Tuple[int, int, int],
    ):
        self.dzi_image = dzi_image
        self.level_index = level_index
        self.xml_path = xml_path
        super().__init__(
            c_axiskeys_on_disk="yx" if num_channels == 1 else "yxc",
            filesystem=filesystem,
            path=DziImageElement.make_level_path(xml_path=xml_path, level_index=level_index),
            tile_shape=dzi_image.get_tile_shape(num_channels=num_channels),
            dtype=np.dtype("uint8"),
            interval=dzi_image.get_shape(level_index=level_index, num_channels=num_channels).to_interval5d(),
            spatial_resolution=spatial_resolution, #FIXME: maybe delete this altogether?
        )

    def to_dto(self) -> DziLevelDataSourceDto:
        raise NotImplementedError #FIXME
        # return DziLevelDataSourceDto(
        #     level=self.level.to_dto()
        # )

    @staticmethod
    def from_dto(dto: DziLevelDataSourceDto) -> "DziLevelDataSource | Exception":
        raise NotImplementedError #FIXME
        # level = DziLevel.from_dto(dto.level)
        # if isinstance(level, Exception):
        #     return level
        # return DziLevelDataSource(level=level)

    @classmethod
    def try_load_pyramid(
        cls, *, filesystem: IFilesystem, dzi_path: PurePosixPath
    ) -> "Mapping[int, DziLevelDataSource] | FsFileNotFoundException | Exception":
        dzi_image_element = DziImageElement.try_load(filesystem=filesystem, path=dzi_path)
        if isinstance(dzi_image_element, Exception):
            return dzi_image_element

        num_channels: int
        for level_index in range(dzi_image_element.num_levels):
            level_path = DziImageElement.make_level_path(xml_path=dzi_path, level_index=level_index)
            first_tile_path = level_path / f"0_0.{dzi_image_element.Format}"
            contents_result = filesystem.read_file(first_tile_path)
            if isinstance(contents_result, FsFileNotFoundException):
                continue
            if isinstance(contents_result, Exception):
                return contents_result
            file_like = io.BytesIO(contents_result)
            try:
                pil_image = PilImage.open(file_like)
            except Exception:
                return GarbledTileException(first_tile_path)
            num_channels = len(pil_image.getbands())
            if num_channels not in (1, 3):
                return GarbledTileException(first_tile_path) #FIXME: better error type?
            break
        else:
            return Exception("Could not determine number of channels")

        datasources: Dict[int, DziLevelDataSource] = {}
        height = dzi_image_element.Size.Height
        width = dzi_image_element.Size.Width
        for level_index, _ in enumerate(dzi_image_element.levels):
            datasources[level_index] = DziLevelDataSource(
                filesystem=filesystem,
                level_index=level_index,
                dzi_image=dzi_image_element,
                num_channels=num_channels,
                xml_path=dzi_path,
                spatial_resolution=(1,1,1), #FIXME,
            )
            width = math.ceil(width / 2)
            height = math.ceil(height / 2)
        return datasources

    @classmethod
    def try_load(
        cls,
        *,
        filesystem: IFilesystem,
        level_path: PurePosixPath,
    ) -> "DziLevelDataSource | Exception":
        level_index = DziImageElement.get_level_index_from_path(level_path)
        if not DziImageElement.is_level_path(level_path) or isinstance(level_index, Exception):
            return Exception(f"Unsupported url: {filesystem.geturl(path=level_path)}")
        possible_dzi_paths = [
            level_path.parent.parent / level_path.parent.name.replace("_files", suffix)
            for suffix in (".dzi", ".xml")
        ]
        for dzi_path in possible_dzi_paths:
            pyramid_result = cls.try_load_pyramid(filesystem=filesystem, dzi_path=dzi_path)
            if isinstance(pyramid_result, FsFileNotFoundException):
                continue
            if isinstance(pyramid_result , Exception):
                return pyramid_result
            return pyramid_result.get(level_index, Exception(f"Level {level_index} does not exist in {filesystem.geturl(path=level_path)}"))
        return Exception(f"Could not open dzi file at any of {possible_dzi_paths}")

    @classmethod
    def supports_path(cls, path: PurePosixPath) -> bool:
        return DziImageElement.is_level_path(path)

    def __hash__(self) -> int:
        return hash(self.url)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, DziLevelDataSource) and
            self.url == other.url
        )

    def _get_tile(self, tile: Interval5D) -> Array5D:
        assert tile.is_tile(tile_shape=self.tile_shape, full_interval=self.interval, clamped=True), f"Bad tile: {tile}"
        tile_path = self.dzi_image.get_tile_path(level_path=self.path, tile=tile)
        raw_tile_bytes = self.filesystem.read_file(tile_path)
        if isinstance(raw_tile_bytes, FsFileNotFoundException):
            logger.warn(f"tile {tile} not found. Returning zeros")
            return Array5D.allocate(interval=tile, dtype=self.dtype, value=0)
        if isinstance(raw_tile_bytes, Exception):
            raise raw_tile_bytes #FIXME: return instead
        file_like = io.BytesIO(raw_tile_bytes)
        try:
            pil_image = PilImage.open(file_like)
        except Exception:
            raise GarbledTileException(tile_path) #FIXME: return instead
        raw_tile_array = np.array(pil_image)

        return Array5D(
            raw_tile_array,
            axiskeys="yxc"[0:len(raw_tile_array.shape)],
            location=tile.enlarged(radius=Point5D(x=self.dzi_image.Overlap, y=self.dzi_image.Overlap)).clamped(self.interval).start,
        ).cut(interval=tile)
