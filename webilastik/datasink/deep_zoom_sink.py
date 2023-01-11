import io

import numpy as np
from PIL import Image as PilImage
from ndstructs.array5D import Array5D

from webilastik.datasink import FsDataSink, IDataSinkWriter
from webilastik.datasource.deep_zoom_datasource import DziImageElement, DziLevel, DziLevelDataSource, DziSizeElement
from webilastik.server.rpc.dto import DziLevelSinkDto
from webilastik.datasink import FsDataSink

class DziLevelWriter(IDataSinkWriter):
    def __init__(self, data_sink: "DziLevelSink") -> None:
        super().__init__()
        self._data_sink = data_sink

    @property
    def data_sink(self) -> "DziLevelSink":
        return self._data_sink

    def write(self, data: Array5D):
        tile = data.interval
        assert tile.is_tile(tile_shape=self._data_sink.tile_shape, full_interval=self._data_sink.interval, clamped=True), f"Bad tile: {tile}"
        chunk_path = self._data_sink.level.get_tile_path(data.interval)

        out_image = PilImage.fromarray(data.raw("yxc").astype(np.uint8)) # type: ignore
        out_file = io.BytesIO()
        out_image.save(out_file, self._data_sink.level.image_format)
        _ = out_file.seek(0)
        contents = out_file.read() # FIXME: read() ?

        result = self._data_sink.filesystem.create_file(path=chunk_path, contents=contents)
        if isinstance(result, Exception):
            raise result #FIXME


class DziLevelSink(FsDataSink):
    def __init__(
        self,
        *,
        level: DziLevel
    ):
        super().__init__(
            dtype=level.dtype,
            filesystem=level.filesystem,
            interval=level.shape.to_interval5d(),
            path=level.level_path,
            resolution=level.spatial_resolution,
            tile_shape=level.tile_shape,
        )
        self.level = level
        self.dzi_image_element = DziImageElement(
            Format=level.image_format,
            Overlap=level.overlap,
            Size=DziSizeElement(Width=level.shape.x, Height=level.shape.y),
            TileSize=level.tile_shape.x,
        )

    def open(self) -> "Exception | DziLevelWriter":
        for dzi_path in self.level.possible_dzi_paths:
            existing_dzi = DziImageElement.try_load(filesystem=self.level.filesystem, path=dzi_path)
            if isinstance(existing_dzi, Exception):
                continue
            if existing_dzi.Size.Width != self.dzi_image_element:
                return Exception(f"Incompatible existing .dzi at {self.level.filesystem.geturl(dzi_path)}")
            break
        else:
            dzi_write_result = self.level.filesystem.create_file(
                path=self.level.possible_dzi_paths[0], contents=self.dzi_image_element.to_string().encode("utf8")
            )
            if isinstance(dzi_write_result, Exception):
                return dzi_write_result
        return DziLevelWriter(data_sink=self)

    def to_datasource(self) -> DziLevelDataSource:
        raise Exception(f"FIXME")

    def to_dto(self) -> DziLevelSinkDto:
        return DziLevelSinkDto(level=self.level.to_dto())

    @classmethod
    def from_dto(cls, dto: DziLevelSinkDto) -> "DziLevelSink | Exception":
        level = DziLevel.from_dto(dto.level)
        if isinstance(level, Exception):
            return level
        return DziLevelSink(
            level=level
        )
