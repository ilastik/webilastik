from typing import List, Literal, cast, Final, Tuple
from pathlib import PurePosixPath
from dataclasses import dataclass
import math

from webilastik.server.rpc.dto import DziImageElementDto, DziSizeElementDto

from ndstructs.point5D import Interval5D, Shape5D
from xml.etree import ElementTree
import defusedxml.ElementTree as DefusedET # type: ignore
ET = cast(ElementTree, DefusedET) # thre are type stubs for ElementTree but not for DefusedET

from webilastik.filesystem import FsFileNotFoundException, FsIoException, IFilesystem


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

@dataclass
class Rect:
    width: int
    height: int

@dataclass
class DziSizeElement:
    Width: Final[int]
    Height: Final[int]

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, DziSizeElement) and
            self.Width == other.Width and
            self.Height == other.Height
        )

    @classmethod
    def from_element(cls, element: ElementTree.Element) -> "DziSizeElement | DziParsingException":
        Width_result = _try_get_int_attr(attr_name="Width", element=element)
        if isinstance(Width_result, Exception):
            return Width_result
        Height_result = _try_get_int_attr(attr_name="Height", element=element)
        if isinstance(Height_result, Exception):
            return Height_result
        return DziSizeElement(Width=Width_result, Height=Height_result)

    @classmethod
    def from_dto(cls, dto: DziSizeElementDto) -> "DziSizeElement":
        return DziSizeElement(Height=dto.Height, Width=dto.Width)

    def to_dto(self) -> DziSizeElementDto:
        return DziSizeElementDto(Height=self.Height, Width=self.Width)

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
class DziImageElement:
    DZI_XML_SUFFIXES: Final[Tuple[str, str]] = (".xml", ".dzi")
    def __init__(self, *, Format: ImageFormat, Overlap: int, TileSize: int, Size: DziSizeElement) -> None:
        self.Format: Final[ImageFormat] = Format
        self.Overlap: Final[int] = Overlap
        self.TileSize: Final[int] = TileSize
        self.Size: Final[DziSizeElement] = Size

        self.max_level_index: Final[int] = math.ceil(math.log(max(self.Size.Height, self.Size.Width), 2))
        self.num_levels = self.max_level_index + 1

        self.levels: List[Rect] = []

        width: int = self.Size.Width
        height: int = self.Size.Height
        for _ in range(self.num_levels):
            self.levels.insert(0, Rect(width=width, height=height))
            width = math.ceil(width / 2)
            height = math.ceil(height / 2)

        super().__init__()

    @classmethod
    def from_dto(cls, dto: DziImageElementDto) -> "DziImageElement":
        return DziImageElement(
            Format=dto.Format,
            Overlap=dto.Overlap,
            Size=DziSizeElement.from_dto(dto.Size),
            TileSize=dto.TileSize,
        )

    def to_dto(self) -> DziImageElementDto:
        return DziImageElementDto(
            Format=self.Format,
            Overlap=self.Overlap,
            Size=self.Size.to_dto(),
            TileSize=self.TileSize,
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, DziImageElement) and
            self.Format == other.Format and
            self.Overlap == other.Overlap and
            self.TileSize == other.TileSize and
            self.Size == other.Size
        )

    def get_shape(self, num_channels: int, level_index: int) -> Shape5D:
        return Shape5D(x=self.levels[level_index].width, y=self.levels[level_index].height, c=num_channels)

    def get_tile_shape(self, num_channels: int) -> Shape5D:
        return Shape5D(x=self.TileSize, y=self.TileSize, c=num_channels)

    @classmethod
    def make_level_path(cls, xml_path: PurePosixPath, level_index: int) -> PurePosixPath:
        return xml_path.parent / f"{xml_path.stem}_files/{level_index}"

    @classmethod
    def get_level_index_from_path(cls, level_path: PurePosixPath) -> "int | Exception":
        try:
            return int(level_path.name)
        except:
            return Exception(f"Could not get path index from path {level_path}")

    @classmethod
    def is_level_path(cls, path: PurePosixPath) -> bool:
        if isinstance(cls.get_level_index_from_path(path), Exception):
            return False
        return path.parent.name.endswith("_files")

    @classmethod
    def dzi_paths_from_level_path(cls, level_path: PurePosixPath) -> Tuple[PurePosixPath, PurePosixPath]:
        xml_file_stem = level_path.parent.name[:-len("_files")]
        return (
           level_path.parent.parent / f"{xml_file_stem}.xml",
           level_path.parent.parent / f"{xml_file_stem}.dzi",
        )

    def get_tile_path(self, *, level_path: PurePosixPath, tile: Interval5D) -> PurePosixPath:
        column = tile.x[0] // self.TileSize
        row = tile.y[0] // self.TileSize
        return level_path / f"{column}_{row}.{self.Format.lower()}"

    @classmethod
    def try_from_element(cls, element: ElementTree.Element) -> "DziImageElement | DziParsingException":
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

    @classmethod
    def try_load(cls, filesystem: IFilesystem, path: PurePosixPath) -> "DziImageElement | FsIoException | FsFileNotFoundException | DziParsingException":
        dzi_xml = filesystem.read_file(path)
        if isinstance(dzi_xml, Exception):
            return dzi_xml
        try:
            element = ET.fromstring(dzi_xml.decode("utf8")) # FIXME: utf8? it's a MS format, maybe something closer to utf16?
        except Exception:
            return DziParsingException(f"Could not parse data in {filesystem.geturl(path)} as XML")
        return DziImageElement.try_from_element(element)

    def to_string(self) -> str:
        return f"""<?xml version="1.0" encoding="utf-8"?>
            <Image TileSize="{self.TileSize}" Overlap="{self.Overlap}" Format="{self.Format}"
                xmlns="http://schemas.microsoft.com/deepzoom/2008">
                <Size Width="{self.Size.Width}" Height="{self.Size.Height}"/>
            </Image>
        """