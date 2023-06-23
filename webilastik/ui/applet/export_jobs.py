# pyright: strict

from abc import  ABC
from dataclasses import dataclass
import math
from pathlib import PurePosixPath
from typing import Literal, cast, Any, Callable, Sequence, TypeVar, Iterable, Generic
from functools import partial
import uuid
from zipfile import ZipFile, ZIP_STORED

from ndstructs.point5D import Interval5D, Point5D
from ndstructs.array5D import Array5D
import numpy as np
from skimage.transform import resize_local_mean #pyright: ignore [reportMissingTypeStubs, reportUnknownVariableType]

from webilastik.datasource import DataRoi, DataSource
from webilastik.datasink import DataSink, IDataSinkWriter
from webilastik.datasink.deep_zoom_sink import DziLevelSink, DziLevelWriter
from webilastik.datasource.deep_zoom_image import DziImageElement
from webilastik.datasource.deep_zoom_image import DziImageElement
from webilastik.filesystem import FsIoException, FsFileNotFoundException, IFilesystem
from webilastik.filesystem.os_fs import OsFs
from webilastik.operator import Operator
from webilastik.scheduling.job import Job, JobProgressCallback, JobStatus
from webilastik.server.rpc.dto import ExportJobDto, ZipJobDto, CreateDziPyramidJobDto


IN = TypeVar("IN")
OUT = TypeVar("OUT")
class FallibleJob(Job[OUT], ABC): #FIXME: generic over Exception type>
    def __init__(
        self,
        *,
        name: str,
        target: Callable[[IN], OUT],
        on_progress: "JobProgressCallback[OUT] | None" = None,
        args: Iterable[IN],
        num_args: "int | None" = None,
    ):
        self.error_message: "str | None" = None #FIXME: looks like error_message could exist when status != 'completed'

        def wrapped_on_progress(*, job_id: uuid.UUID, job_status: JobStatus, step_index: int, step_result: OUT):
            if isinstance(step_result, Exception) and self.error_message is None:
                self.error_message = str(step_result)
            if on_progress:
                on_progress(job_id=job_id, job_status=job_status, step_index=step_index, step_result=step_result)

        super().__init__(
            name=name,
            target=target,
            on_progress=wrapped_on_progress,
            args=args,
            num_args=num_args,
        )

class OpenDatasinkJob(FallibleJob["IDataSinkWriter | Exception"]):
    def __init__(
        self,
        *,
        on_complete: JobProgressCallback["IDataSinkWriter | Exception"],
        datasink: DataSink,
    ):
        super().__init__(
            name="Creating datasink",
            target=OpenDatasinkJob._open_datasink,
            on_progress=on_complete,
            args=[datasink],
            num_args=1
        )
        self.datasink = datasink

    @staticmethod
    def _open_datasink(ds: DataSink) -> "IDataSinkWriter | Exception":
        return ds.open()

    def to_dto(self) -> ExportJobDto:
        with self.job_lock:
            return ExportJobDto( #FIXME: OpenDataSinkJobDto or something?
                name=self.name,
                num_args=self.num_args,
                uuid=str(self.uuid),
                status=self._status,
                num_completed_steps=self.num_completed_steps,
                error_message=self.error_message,
                datasink=self.datasink.to_dto()
            )


@dataclass
class _ExportTask(Generic[IN]):
    operator: Operator[IN, Array5D]
    sink_writer: IDataSinkWriter

    def __call__(self, step_arg: IN) -> "None | Exception":
        tile = self.operator(step_arg)
        print(f"Writing tile {tile}")
        return self.sink_writer.write(tile)

class ExportJob(FallibleJob["None | Exception"]):
    def __init__(
        self,
        *,
        name: str,
        on_progress: "JobProgressCallback[None | Exception]",
        operator: Operator[DataRoi, Array5D],
        sink_writer: IDataSinkWriter,
        args: Iterable[DataRoi],
        num_args: "int | None" = None,
    ):
        super().__init__(
            name=name,
            target=_ExportTask(operator=operator, sink_writer=sink_writer),
            on_progress=on_progress,
            args=args,
            num_args=num_args
        )
        self.sink_writer = sink_writer

    def to_dto(self) -> ExportJobDto:
        with self.job_lock:
            return ExportJobDto(
                name=self.name,
                num_args=self.num_args,
                uuid=str(self.uuid),
                status=self._status,
                num_completed_steps=self.num_completed_steps,
                error_message=self.error_message,
                datasink=self.sink_writer.data_sink.to_dto()
            )


class DownscaleDatasource(FallibleJob["DziLevelSink | Exception"]):
    def __init__(
        self,
        *,
        name: str,
        source: DataSource,
        sink_writer: DziLevelWriter,
        on_progress: JobProgressCallback["DziLevelSink | Exception"],
    ):
        sink = sink_writer.data_sink
        super().__init__(
            name=name,
            target=partial(DownscaleDatasource.downscale, source=source, sink_writer=sink_writer),
            on_progress=on_progress,
            args=sink.interval.split(sink.tile_shape),
            num_args=sink.interval.get_num_tiles(tile_shape=sink.tile_shape)
        )
        self.sink_writer = sink_writer

    @staticmethod
    def downscale(sink_tile: Interval5D, source: DataSource, sink_writer: DziLevelWriter) -> "DziLevelSink | Exception":
        sink = sink_writer.data_sink
        ratio_x = source.shape.x / sink.shape.x
        ratio_y = source.shape.y / sink.shape.y
        ratio_z = source.shape.z / sink.shape.z

        for sink_tile in sink.interval.split(sink.tile_shape):
            sink_roi_plus_halo = sink_tile.enlarged(radius=Point5D(x=1, y=1)).clamped(sink.interval)

            source_interval_plus_halo = Interval5D.zero(
                x=(
                    math.floor(sink_roi_plus_halo.start.x * ratio_x),
                    math.ceil(sink_roi_plus_halo.stop.x * ratio_x)
                ),
                y=(
                    math.floor(sink_roi_plus_halo.start.y * ratio_y),
                    math.ceil(sink_roi_plus_halo.stop.y * ratio_y)
                ),
                z=(
                    math.floor(sink_roi_plus_halo.start.z * ratio_z),
                    math.ceil(sink_roi_plus_halo.stop.z * ratio_z)
                ),
                c=source.interval.c,
            ).clamped(source.interval)

            source_data_with_halo = source.retrieve(source_interval_plus_halo)

            sink_tile_data_with_halo_raw: np.ndarray[Any, np.dtype[np.float32]] = cast(
                "np.ndarray[Any, np.dtype[np.float32]]",
                resize_local_mean(
                    image=source_data_with_halo.raw("zyxc"),
                    channel_axis=3,
                    output_shape=sink_roi_plus_halo.shape.to_tuple("zyx"),
                )
            )

            sink_tile_data_with_halo = Array5D(sink_tile_data_with_halo_raw, axiskeys="zyxc", location=sink_roi_plus_halo.start).as_uint8()
            sink_tile_data = sink_tile_data_with_halo.cut(sink_tile)

            writing_result = sink_writer.write(sink_tile_data)
            if isinstance(writing_result, Exception):
                return writing_result
        return sink

    def to_dto(self) -> ExportJobDto: #FIXME?
        with self.job_lock:
            return ExportJobDto(
                name=self.name,
                num_args=self.num_args,
                uuid=str(self.uuid),
                status=self._status,
                num_completed_steps=self.num_completed_steps,
                error_message=self.error_message,
                datasink=self.sink_writer.data_sink.to_dto()
            )


class CreateDziPyramid(FallibleJob["Sequence[DziLevelSink] | Exception"]):
    def __init__(
        self,
        *,
        name: str,
        filesystem: IFilesystem,
        xml_path: PurePosixPath,
        dzi_image: DziImageElement,
        num_channels: Literal[1, 3],
        on_complete: Callable[[uuid.UUID, "Sequence[DziLevelSink] | Exception"], Any],
    ):

        target = partial(
            DziLevelSink.create_pyramid,
            xml_path=xml_path,
            dzi_image=dzi_image,
            num_channels=num_channels
        )

        def on_progress(*, job_id: uuid.UUID, job_status: JobStatus, step_index: int, step_result: "Sequence[DziLevelSink] | Exception"):
            on_complete(job_id, step_result)

        super().__init__(
            name=name,
            target=target,
            args=[filesystem],
            num_args=1,
            on_progress=on_progress,
        )

    def to_dto(self) -> CreateDziPyramidJobDto: #FIXME?
        with self.job_lock:
            return CreateDziPyramidJobDto(
                name=self.name,
                num_args=self.num_args,
                uuid=str(self.uuid),
                status=self._status,
                num_completed_steps=self.num_completed_steps,
                error_message=self.error_message,
            )


class ZipDirectory(FallibleJob["None | Exception"]):
    def __init__(
        self,
        *,
        name: str,
        output_fs: IFilesystem,
        output_path: PurePosixPath,
        input_fs: IFilesystem,
        input_directory: PurePosixPath,
        delete_source: bool,
        on_progress: "JobProgressCallback[Exception | None] | None" = None,
    ):
        super().__init__(
            name=name,
            target=partial(
                ZipDirectory.zip_directory,
                input_fs=input_fs,
                output_fs=output_fs,
                output_path=output_path,
                delete_source=delete_source
            ),
            on_progress=on_progress,
            args=[input_directory],
            num_args=1,
        )
        self.output_fs = output_fs
        self.output_path = output_path

    @classmethod
    def zip_directory(
        cls,
        input_directory: PurePosixPath,
        /, *,
        input_fs: IFilesystem,
        output_fs: IFilesystem,
        output_path: PurePosixPath,
        delete_source: bool,
    ) -> "None | Exception":
        temp_fs = OsFs.create_scratch_dir()
        if isinstance(temp_fs, Exception):
            return temp_fs
        tmp_zip_file_path = PurePosixPath("/out.zip")

        try:
            zip_file = ZipFile(temp_fs.resolve_path(tmp_zip_file_path), mode="w", compresslevel=ZIP_STORED)
        except Exception as e:
            return FsIoException(e)

        def write_to_zip(dir_path: PurePosixPath) -> "None | FsIoException | FsFileNotFoundException":
            dir_contents_result = input_fs.list_contents(dir_path)
            if isinstance(dir_contents_result, Exception):
                return dir_contents_result

            for file_path in dir_contents_result.files:
                data_result = input_fs.read_file(file_path)
                if isinstance(data_result, Exception):
                    return data_result
                arcname = file_path.relative_to(input_directory)
                try:
                    zip_file.writestr(arcname.as_posix(), data_result)
                except Exception as e:
                    return FsIoException(e)

            for subdir_path in dir_contents_result.directories:
                writing_result = write_to_zip(subdir_path)
                if isinstance(writing_result, Exception):
                    return writing_result

        zipping_result = write_to_zip(input_directory)
        if isinstance(zipping_result, Exception):
            return zipping_result
        zip_file.close()

        write_result = output_fs.transfer_file(
            source_fs=temp_fs, source_path=tmp_zip_file_path, target_path=output_path
        )
        _ = temp_fs.delete(tmp_zip_file_path)

        if delete_source:
            _ = temp_fs.delete(PurePosixPath("/"))

        if isinstance(write_result, Exception):
            return write_result


    def to_dto(self) -> ZipJobDto:
        with self.job_lock:
            return ZipJobDto(
                error_message=self.error_message,
                name=self.name,
                num_args=self.num_args,
                num_completed_steps=self.num_completed_steps,
                status=self._status,
                uuid=str(self.uuid),
                output_fs=self.output_fs.to_dto(),
                output_path=self.output_path.as_posix(),
            )