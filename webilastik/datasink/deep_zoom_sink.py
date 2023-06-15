import io
from pathlib import PurePosixPath
from typing import List, Literal, Sequence, cast

import numpy as np
from PIL import Image as PilImage
from ndstructs.array5D import Array5D

from webilastik.datasink import FsDataSink, IDataSinkWriter
from webilastik.datasource.deep_zoom_datasource import DziImageElement, DziLevelDataSource
from webilastik.filesystem import FsIoException, IFilesystem, create_filesystem_from_message
from webilastik.server.rpc.dto import DziLevelSinkDto
from webilastik.datasink import FsDataSink

class DziLevelWriter(IDataSinkWriter):
    def __init__(self, data_sink: "DziLevelSink") -> None:
        super().__init__()
        self._data_sink = data_sink

    @property
    def data_sink(self) -> "DziLevelSink":
        return self._data_sink

    def write(self, data: Array5D) -> "None | FsIoException":
        tile = data.interval
        assert tile.is_tile(tile_shape=self._data_sink.tile_shape, full_interval=self._data_sink.interval, clamped=True), f"Bad tile: {tile}"
        chunk_path = self._data_sink.dzi_image.get_tile_path(level_path=self._data_sink.path, tile=data.interval)

        raw_axiskeys = "yxc" if data.shape.c > 1 else "yx"
        out_image = PilImage.fromarray(data.raw(raw_axiskeys).astype(np.uint8)) # type: ignore
        out_file = io.BytesIO()
        out_image.save(out_file, self._data_sink.dzi_image.Format.replace("jpg", "jpeg"))
        _ = out_file.seek(0)
        contents = out_file.read() # FIXME: read() ?

        return self._data_sink.filesystem.create_file(path=chunk_path, contents=contents)


class DziLevelSink(FsDataSink):
    class __PrivateMarker:
        pass

    def __init__(
        self,
        *,
        private_marker: __PrivateMarker,
        filesystem: IFilesystem,
        xml_path: PurePosixPath,
        dzi_image: DziImageElement,
        num_channels: Literal[1, 3],
        level_index: int,
    ):
        self.dzi_image = dzi_image
        self.level_index = level_index
        self.xml_path = xml_path
        super().__init__(
            filesystem=filesystem,
            path=DziImageElement.make_level_path(xml_path=xml_path, level_index=level_index),
            tile_shape=dzi_image.get_tile_shape(num_channels=num_channels),
            dtype=np.dtype("uint8"),
            interval=dzi_image.get_shape(level_index=level_index, num_channels=num_channels).to_interval5d(),
        )

    def open(self) -> "DziLevelWriter":
        return DziLevelWriter(data_sink=self)

    @classmethod
    def create_pyramid(
        cls,
        filesystem: IFilesystem,
        xml_path: PurePosixPath,
        dzi_image: DziImageElement,
        num_channels: Literal[1, 3],
    ) -> "Sequence[DziLevelSink] | Exception":
        if xml_path.suffix.lower() not in (".dzi", ".xml") :
            return Exception(f"Bad dzi path {xml_path}. Must end in .dzi or .xml")
        resp = filesystem.create_file(path=xml_path, contents=dzi_image.to_string().encode("utf8"))
        if isinstance(resp, Exception):
            return resp

        out: List[DziLevelSink] = []

        for level_index, _ in enumerate(dzi_image.levels):
            level_path = DziImageElement.make_level_path(xml_path=xml_path, level_index=level_index)
            resp = filesystem.create_directory(path=level_path)
            if isinstance(resp, Exception):
                return resp
            level_sink = DziLevelSink(
                private_marker=cls.__PrivateMarker(),
                filesystem=filesystem,
                dzi_image=dzi_image,
                level_index=level_index,
                num_channels=num_channels,
                xml_path=xml_path,
            )
            out.append(level_sink)
        return out

    def to_datasource(self) -> DziLevelDataSource:
        raise Exception(f"FIXME")

    def to_dto(self) -> DziLevelSinkDto:
        num_channels = cast(Literal[1, 3], self.shape.c)
        return DziLevelSinkDto(
            dzi_image=self.dzi_image.to_dto(),
            filesystem=self.filesystem.to_dto(),
            level_index=self.level_index,
            num_channels=num_channels,
            xml_path=self.xml_path.as_posix(),
        )

    @classmethod
    def from_dto(cls, dto: DziLevelSinkDto) -> "DziLevelSink | Exception":
        fs_result = create_filesystem_from_message(dto.filesystem)
        if isinstance(fs_result, Exception):
            return fs_result

        return DziLevelSink(
            dzi_image=DziImageElement.from_dto(dto.dzi_image),
            filesystem=fs_result,
            level_index=dto.level_index,
            num_channels=dto.num_channels,
            xml_path=PurePosixPath(dto.xml_path),
            private_marker=cls.__PrivateMarker(),
        )
