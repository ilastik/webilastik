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
from webilastik.datasource.deep_zoom_image import DziImageElement, DziParsingException, GarbledTileException
from webilastik.filesystem import FsFileNotFoundException, FsIoException, IFilesystem
from webilastik.filesystem import zip_fs
from webilastik.filesystem.zip_fs import ZipFs
from webilastik.server.rpc.dto import DziLevelDataSourceDto
from webilastik.filesystem import FsFileNotFoundException, IFilesystem
from webilastik.utility.url import Url


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

    @property
    def url(self) -> Url:
        return self.filesystem.geturl(self.xml_path).updated_with(hash_=f"level={self.level_index}")

    @classmethod
    def get_level_from_url(cls, url: Url) -> "int | None | Exception":
        level_str = url.get_hash_params().get("level")
        if level_str is None:
            return None
        try:
            return int(level_str)
        except Exception:
            return Exception(f"Bad level fragment parameter: {level_str}")

    def to_dto(self) -> DziLevelDataSourceDto:
        raise NotImplementedError #FIXME

    @staticmethod
    def from_dto(dto: DziLevelDataSourceDto) -> "DziLevelDataSource | Exception":
        raise NotImplementedError #FIXME

    @classmethod
    def try_load(
        cls, *, filesystem: IFilesystem, path: PurePosixPath
    ) -> "Mapping[int, DziLevelDataSource] | None | FsFileNotFoundException | Exception":
        out = cls.try_load_as_dzip(filesystem=filesystem, dzip_path=path)
        if out is not None:
            return out
        return cls.try_load_as_pyramid(filesystem=filesystem, dzi_path=path)

    @classmethod
    def try_load_as_dzip(
        cls, *, filesystem: IFilesystem, dzip_path: PurePosixPath
    ) -> "Mapping[int, DziLevelDataSource] | None | FsFileNotFoundException | FsIoException | DziParsingException":
        if dzip_path.suffix.lower() != ".dzip":
            return None
        zip_fs_result = ZipFs.create(zip_file_fs=filesystem, zip_file_path=dzip_path)
        if isinstance(zip_fs, FsFileNotFoundException):
            return None
        if isinstance(zip_fs_result, Exception):
            return zip_fs_result
        dzip_contents = zip_fs_result.list_contents(PurePosixPath("/"))
        if isinstance(dzip_contents, Exception):
            return dzip_contents
        for f in sorted(dzip_contents.files):
            pyramid_result = cls.try_load_as_pyramid(filesystem=zip_fs_result, dzi_path=f)
            if pyramid_result is None:
                continue
            return pyramid_result
        return None

    @classmethod
    def try_load_as_pyramid(
        cls, *, filesystem: IFilesystem, dzi_path: PurePosixPath
    ) -> "Mapping[int, DziLevelDataSource] | None | FsFileNotFoundException | FsIoException | DziParsingException":
        if dzi_path.suffix.lower() not in DziImageElement.DZI_XML_SUFFIXES:
            return None
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
            return FsFileNotFoundException(DziImageElement.make_level_path(xml_path=dzi_path, level_index=0) / "0_0") #FIXME

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
    def supports_path(cls, path: PurePosixPath) -> bool:
        return DziImageElement.is_level_path(path) or path.suffix.lower() in (".xml", ".dzi", ".dzip")

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
