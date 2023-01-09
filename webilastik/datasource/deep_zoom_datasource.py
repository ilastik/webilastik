# pyright: strict

from dataclasses import dataclass
from typing import Dict, Literal, Mapping, Tuple, Any, cast
from pathlib import PurePosixPath
import logging
import io
import math

import numpy as np
from PIL import Image as PilImage
from ndstructs.point5D import Point5D, Shape5D, Interval5D
from ndstructs.array5D import Array5D

from webilastik.datasource import FsDataSource
from webilastik.filesystem import FsFileNotFoundException, IFilesystem
from webilastik.utility.url import Url
from webilastik.server.rpc.dto import PrecomputedChunksDataSourceDto


logger = logging.getLogger(__name__)

from xml.etree import ElementTree
import defusedxml.ElementTree as DefusedET # type: ignore
ET = cast(ElementTree, DefusedET)


class DziParsingException(Exception):
    pass

class MissingAttribute(DziParsingException):
    def __init__(self, attr_name: str) -> None:
        super().__init__(f"Missing attribute {attr_name}")

class MissingChild(DziParsingException):
    def __init__(self, child_name: str) -> None:
        super().__init__(f"Missing child '{child_name}'")

class BadDziAttrValue(DziParsingException):
    def __init__(self, *, name: str, raw_value: str) -> None:
        super().__init__(f"Bad value for {name}: '{raw_value}'")

class LevelDoesntExistException(DziParsingException):
    def __init__(self, level: int) -> None:
        super().__init__(f"DZI Zoom Level does not exist: {level}")

class GarbledTileException(DziParsingException):
    def __init__(self, path: PurePosixPath) -> None:
        super().__init__(f"Garbled tile at {path}")

def _try_get_int_attr(attr_name: str, element: ElementTree.Element) -> "int | DziParsingException":
    raw_value = element.attrib.get(attr_name)
    if raw_value is None:
        return MissingAttribute(attr_name)
    try:
        return int(raw_value)
    except Exception:
        return BadDziAttrValue(name=attr_name, raw_value=raw_value)

ImageFormat = Literal["jpeg", "jpg", "png"]

class DziSizeElement:
    def __init__(self, Width: int, Height: int) -> None:
        super().__init__()
        self.Width = Width
        self.Height = Height

    @classmethod
    def from_element(cls, element: ElementTree.Element) -> "DziSizeElement | DziParsingException":
        Width_result = _try_get_int_attr(attr_name="Width", element=element)
        if isinstance(Width_result, Exception):
            return Width_result
        Height_result = _try_get_int_attr(attr_name="Height", element=element)
        if isinstance(Height_result, Exception):
            return Height_result
        return DziSizeElement(Width=Width_result, Height=Height_result)


@dataclass
class DziImageElement:
    Format: ImageFormat
    Overlap: int
    TileSize: int
    Size: DziSizeElement

    @classmethod
    def try_from_element(cls, element: ElementTree.Element) -> "DziImageElement | Exception":
        xmlns = element.tag[0: -len("Image")]

        Format = element.attrib.get("Format")
        if not Format:
            return DziParsingException("Missing Format")
        Format = Format.lower()
        if Format not in ("jpeg", "jpg", "png"):
            return DziParsingException(f"Bad format: {Format}")
        Overlap_result = _try_get_int_attr("Overlap", element=element)
        if isinstance(Overlap_result, Exception):
            return Overlap_result
        if Overlap_result < 0:
            return DziParsingException(f"Bad overlap value")
        TileSize_result = _try_get_int_attr("TileSize", element=element)
        if isinstance(TileSize_result, Exception):
            return TileSize_result

        size_node = element.find(xmlns + "Size")
        if size_node is None:
            return MissingChild("Size")
        Size_result = DziSizeElement.from_element(size_node)
        if isinstance(Size_result, Exception):
            return Size_result

        return DziImageElement(
            Format=Format,
            Overlap=Overlap_result,
            TileSize=TileSize_result,
            Size=Size_result,
        )

# Each resolution of the pyramid is called a level. Levels are counted from the 1x1 pixel as level 0.
# Each level is the size 2(level)x2(level).
# Each level is stored in a separate folder.
# All levels are stored in a folder with the same name as the DZI file with the extension removed and "_files" appended to it.
#     For example, the pyramid for test.dzi is stored in test_files.
# Each level may be broken up into several tiles.
#     The tiles are named as column_row.format
#         row is the row number of the tile (starting from 0 at top)
#         column is the column number of the tile (starting from 0 at left)
#         format is the appropriate extension for the image format used – either JPEG or PNG.

class DziLevelDataSource(FsDataSource):
    def __init__(
        self,
        *,
        filesystem: IFilesystem,
        level_path: PurePosixPath,
        overlap: int,
        tile_shape: Shape5D,
        interval: Interval5D,
        dtype: "np.dtype[Any]",
        spatial_resolution: Tuple[int, int, int] = (1,1,1),
        image_format: ImageFormat,
    ):
        super().__init__(
            c_axiskeys_on_disk="yx" if interval.shape.c == 1 else "yxc",
            filesystem=filesystem,
            path=level_path,
            tile_shape=tile_shape,
            dtype=dtype,
            interval=interval,
            spatial_resolution=spatial_resolution, #FIXME: maybe delete this altogether?
        )
        level_index = DziLevelDataSource.get_level_index_from_path(level_path)
        assert not isinstance(level_index, Exception)
        self.overlap = overlap
        self.image_format = image_format

    @classmethod
    def try_load_pyramid(
        cls,
        *,
        filesystem: IFilesystem,
        dzi_path: PurePosixPath,
    ) -> "Mapping[int, DziLevelDataSource] | Exception":
        dzi_xml = filesystem.read_file(dzi_path)
        if isinstance(dzi_xml, Exception):
            return dzi_xml

        try:
            element = ET.fromstring(dzi_xml.decode("utf8")) # FIXME: utf8? it's a MS format, maybe something closer to utf16?
        except Exception:
            return DziParsingException(f"Could not parse data in {dzi_path} as XML")

        dzi_image_element = DziImageElement.try_from_element(element)
        if isinstance(dzi_image_element, Exception):
            return dzi_image_element

        max_level_index = math.ceil(math.log(max(dzi_image_element.Size.Height, dzi_image_element.Size.Width), 2))
        num_levels = max_level_index + 1

        num_channels: int
        for level_index in range(num_levels):
            first_tile_path = dzi_path.parent / f"{dzi_path.stem}_files/{level_index}/0_0.{dzi_image_element.Format}"
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
            break
        else:
            return Exception("Could not determine number of channels")

        levels: Dict[int, DziLevelDataSource] = {}
        height = dzi_image_element.Size.Height
        width = dzi_image_element.Size.Width
        for i in reversed(range(num_levels)):
            levels[i] = DziLevelDataSource(
                filesystem=filesystem,
                level_path=dzi_path.parent / f"{dzi_path.stem}_files/{i}",
                overlap=dzi_image_element.Overlap,
                tile_shape=Shape5D(
                    x=dzi_image_element.TileSize,
                    y=dzi_image_element.TileSize,
                    c=num_channels,
                ),
                dtype=np.dtype("uint8"),
                interval=Shape5D(x=width, y=height, c=num_channels).to_interval5d(),
                image_format=dzi_image_element.Format,
            )
            width = math.ceil(width / 2)
            height = math.ceil(height / 2)
        return levels

    @classmethod
    def try_load_level(
        cls,
        *,
        filesystem: IFilesystem,
        level_path: PurePosixPath,
    ) -> "DziLevelDataSource | Exception":
        level_index = cls.get_level_index_from_path(level_path)
        url = filesystem.geturl(path=level_path)
        if not cls.supports_url(url) or isinstance(level_index, Exception):
            return Exception(f"Unsupported url: {url}")
        possible_dzi_paths = [
            level_path.parent.parent / level_path.parent.name.replace("_files", suffix)
            for suffix in (".dzi", ".xml")
        ]
        for dzi_path in possible_dzi_paths:
            pyramid_result = cls.try_load_pyramid(filesystem=filesystem, dzi_path=dzi_path)
            if isinstance(pyramid_result , Exception):
                continue
            return pyramid_result.get(level_index, Exception(f"Level {level_index} does not exist in {url}"))
        else:
            return Exception(f"Could not open dzi file at any of {possible_dzi_paths}")

    @classmethod
    def get_level_index_from_path(cls, path: PurePosixPath) -> "int | Exception":
        try:
            return int(path.name)
        except:
            return Exception(f"Could not get path index from path {path}")

    @classmethod
    def supports_url(cls, url: Url) -> bool:
        if isinstance(cls.get_level_index_from_path(url.path), Exception):
            return False
        return url.path.parent.name.endswith("_files")

    def to_dto(self) -> PrecomputedChunksDataSourceDto:
        raise Exception("FIXME")

    @staticmethod
    def from_dto(dto: PrecomputedChunksDataSourceDto) -> "Exception":
        raise Exception("FIXME")

    def __hash__(self) -> int:
        return hash(self.url)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, DziLevelDataSource) and
            self.url == other.url
        )

    def get_tile_path(self, tile: Interval5D) -> PurePosixPath:
        column = tile.x[0] // self.tile_shape.x
        row = tile.y[0] // self.tile_shape.y
        return self.path / f"{column}_{row}.{self.image_format}"

    def _get_tile(self, tile: Interval5D) -> Array5D:
        assert tile.is_tile(tile_shape=self.tile_shape, full_interval=self.interval, clamped=True), f"Bad tile: {tile}"
        tile_path = self.get_tile_path(tile)
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
            location=tile.enlarged(radius=Point5D(x=self.overlap, y=self.overlap)).clamped(self.interval).start,
        ).cut(interval=tile)
