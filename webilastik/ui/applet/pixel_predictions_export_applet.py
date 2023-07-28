# pyright: strict

from pathlib import PurePosixPath
import threading
from typing import Any, Callable, Dict, Literal, Sequence, TypeVar
import uuid

import numpy as np
from ndstructs.array5D import Array5D
from ndstructs.utils.json_serializable import JsonObject

from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasink import DataSink, FsDataSink, IDataSinkWriter
from webilastik.datasink.deep_zoom_sink import DziLevelSink
from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksSink
from webilastik.datasource import DataRoi, DataSource, FsDataSource
from webilastik.datasource.deep_zoom_image import DziImageElement
from webilastik.datasource.precomputed_chunks_info import RawEncoder
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem import IFilesystem
from webilastik.filesystem.os_fs import OsFs
from webilastik.filesystem.zip_fs import ZipFs
from webilastik.operator import Operator
from webilastik.scheduling.job import Job, JobCanceled, JobFinished, PriorityExecutor, SimpleJob
from webilastik.serialization.json_serialization import JsonValue
from webilastik.server.rpc.dto import (
    MessageParsingError,
    PixelClassificationExportAppletStateDto,
    StartPixelProbabilitiesExportJobParamsDto,
    StartSimpleSegmentationExportJobParamsDto,
)
from webilastik.simple_segmenter import SimpleSegmenter
from webilastik.ui.applet import AppletOutput, StatelesApplet, UserPrompt
from webilastik.ui.applet.export_jobs import CreateDziPyramid, DownscaleDatasource, ExportJob, ZipDirectory
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError
from webilastik.ui.applet.brushing_applet import Label

_OK = TypeVar("_OK")
_ERR = TypeVar("_ERR", bound=Exception)
_SINK = TypeVar("_SINK", bound=DataSink)

# ExportJobUnion = Union[ExportJob, CreateDziPyramid, DownscaleDatasource, ZipDirectory]

class PixelClassificationExportApplet(StatelesApplet):
    def __init__(
        self,
        *,
        name: str,
        on_async_change: Callable[[], Any],
        priority_executor: PriorityExecutor,
        operator: "AppletOutput[VigraPixelClassifier[IlpFilter] | None]",
        populated_labels: "AppletOutput[Sequence[Label] | None]",
        datasource_suggestions: "AppletOutput[Sequence[FsDataSource] | None]"
    ):
        self.on_async_change = on_async_change
        self.priority_executor = priority_executor

        self._in_operator = operator
        self._in_populated_labels = populated_labels
        self._in_datasource_suggestions = datasource_suggestions

        self._jobs: Dict[uuid.UUID, Job[Any, Any]] = {}
        self._lock = threading.Lock()
        super().__init__(name=name)

    def _remove_job(self, job_id: uuid.UUID):
        with self._lock:
            del self._jobs[job_id]

    def _launch_job(self, job: Job[_OK, _ERR], clean_on_success: bool = True, on_success: Callable[[_OK], Any] = lambda _: None): # -> Job[_OK, _ERR]:
        def on_complete(status: "JobCanceled | JobFinished[_OK, _ERR]"):
            if isinstance(status, JobCanceled) or isinstance(status.result, Exception): #FIXME: better typing on checking for exception?
                return
            if clean_on_success:
                self._remove_job(job.uuid)
            self.on_async_change()
            on_success(status.result)
        job.add_done_callback(on_complete)

        print(f"LAUNCHING JOB!!!!!!!!!!!!!!11 {job.name} !!!!!!!!!!!!!!!!!!!!!!!!")
        self.priority_executor.submit_job(job)
        with self._lock:
            self._jobs[job.uuid] = job
        self.on_async_change()
        # return job

    def _launch_open_datasink_job(self, *, datasink: DataSink, on_succcess: Callable[["IDataSinkWriter"], None]):
        return self._launch_job(
            SimpleJob[IDataSinkWriter, Exception](name="Opening data sink", target=datasink.open),
            on_success=on_succcess
        )

    def _launch_export_job(
        self,
        *,
        job_name: str,
        operator: Operator[DataRoi, Array5D],
        datasource: DataSource,
        datasink: DataSink,
        on_success: Callable[[DataSink], Any] = lambda _: None
    ):
        def on_open_datasink_done(sink_writer: IDataSinkWriter):
            export_job = ExportJob(
                name=job_name,
                on_progress=lambda job_id, step_index: self.on_async_change(),
                operator=operator,
                sink_writer=sink_writer,
                args=datasource.roi.split(block_shape=sink_writer.data_sink.tile_shape.updated(c=datasource.shape.c)),
                num_args=datasource.roi.get_num_tiles(tile_shape=sink_writer.data_sink.tile_shape),
            )
            _ = self._launch_job(export_job, on_success=lambda _: on_success(datasink))

        return self._launch_open_datasink_job(datasink=datasink, on_succcess=on_open_datasink_done)

    def _launch_create_dzi_pyramid_job(
        self,
        *,
        name: str,
        filesystem: IFilesystem,
        xml_path: PurePosixPath,
        dzi_image: DziImageElement,
        num_channels: Literal[1, 3],
        on_succcess: Callable[[Sequence[DziLevelSink]], Any] = lambda _: None,
    ) -> None:
        return self._launch_job(CreateDziPyramid(
            name=name,
            filesystem=filesystem,
            dzi_image=dzi_image,
            num_channels=num_channels,
            xml_path=xml_path,
        ), on_success=on_succcess)

    def _launch_downscaling_job(
        self, *, source: DataSource, sink: _SINK, on_success: Callable[[_SINK], Any]
    ):
        def on_sink_opened(sink_writer: IDataSinkWriter):
            downscaling_job = DownscaleDatasource(
                name=f"Downscaling to {sink.shape.x} x {sink.shape.y}{'' if sink.shape.z == 1 else ' ' + str(sink.shape.z)}",
                source=source,
                sink_writer=sink_writer,
                on_progress=lambda job_id, step_index: self.on_async_change(),
            )
            _ = self._launch_job(downscaling_job, on_success=lambda _: on_success(sink))
        return self._launch_open_datasink_job(datasink=sink, on_succcess=on_sink_opened)

    def _launch_convert_to_dzi_job(
        self,
        *,
        datasource: DataSource,
        pyramid: Sequence[DziLevelSink],
        on_succcess: Callable[[Sequence[DziLevelSink]], Any],
    ) -> "None | UsageError":
        def launch_next_downscaling(last_sink: DziLevelSink):
            if last_sink.level_index == 0:
                on_succcess(pyramid)
                return
            _ = self._launch_downscaling_job(
                source=last_sink.to_datasource(),
                sink=pyramid[last_sink.level_index - 1],
                on_success=launch_next_downscaling,
            )

        _ = self._launch_downscaling_job(
            source=datasource,
            sink=pyramid[-1],
            on_success=launch_next_downscaling,
        )

    def _launch_file_transfer_job(
        self,
        *,
        source_fs: IFilesystem,
        source_path: PurePosixPath,
        target_fs: IFilesystem,
        target_path: PurePosixPath,
    ):
        _ = self._launch_job(
            SimpleJob[None, Exception](
                f"Transferring results to {target_fs.geturl(target_path).raw}",
                target=source_fs.transfer_file,
                source_fs=source_fs, source_path=source_path, target_path=target_path,
            ),
            on_success=lambda _: None
        )

    def launch_pixel_probabilities_export_job(self, *, datasource: DataSource, datasink: DataSink) -> "UsageError | None":
        classifier = self._in_operator()
        if classifier is None:
            return UsageError("Upstream not ready yet")
        expected_shape = datasource.shape.updated(c=classifier.num_classes)
        if datasink.shape != expected_shape:
            return UsageError(f"Bad sink shape. Expected {expected_shape} but got {datasink.shape}")
        if datasink.dtype != np.dtype("float32"):
            return UsageError("Data sink should have dtype of float32 for this kind of export")
        if isinstance(datasink, FsDataSink) and isinstance(datasink.filesystem, ZipFs):
            return UsageError("Exporting pixel probabilities to Zip archives is not supported yet")
        _ = self._launch_export_job(job_name="Exporting Pixel Probabilities", operator=classifier, datasource=datasource, datasink=datasink)

    def launch_simple_segmentation_export_job(
        self, *, datasource: DataSource, datasink: DataSink, label_name: str,
    ) -> "UsageError | None":
        with self._lock:
            label_name_indices: Dict[str, int] = {label.name: idx for idx, label in enumerate(self._in_populated_labels() or [])}
            classifier = self._in_operator()
        if label_name not in label_name_indices:
            return UsageError(f"Bad label name: {label_name}")
        if classifier is None:
            return UsageError("Applets upstream are not ready yet")
        if not classifier.is_applicable_to(datasource):
            return UsageError(f"Classifier is not compatible with provided datasource: {datasource}")
        expected_shape = datasource.shape.updated(c=3)
        if datasink.shape != expected_shape:
            return UsageError(f"Data sink shape {datasink.shape} does not meet expectations: {expected_shape}")
        if datasink.dtype != np.dtype("uint8"):
            return UsageError("Data sink should have dtype of 'uint8' for this kind of export")

        segmenter = SimpleSegmenter(preprocessor=classifier, channel_index=label_name_indices[label_name])

        if isinstance(datasink, FsDataSink) and isinstance(datasink.filesystem, ZipFs):
            if not isinstance(datasink, DziLevelSink):
                return UsageError("Exporting to Zip is not supported for non-dzi sinks yet.")

            target_fs = datasink.filesystem.zip_file_fs
            target_dzip_path = datasink.filesystem.zip_file_path


            scratch_fs_result = OsFs.create_scratch_dir()
            if isinstance(scratch_fs_result, Exception):
                print(f"Could not create a local osfs: {scratch_fs_result}")
                return UsageError("IO Error: Could not write to loca filesystem") #FIXME: this is prolly not a usage error
            scratch_fs_dzi_dir_path = PurePosixPath(f"/dzi")
            scratch_fs_xml_path = scratch_fs_dzi_dir_path / datasink.xml_path.as_posix().lstrip("/")
            scratch_fs_dzip_path = PurePosixPath("/final_export/output.dzip")

            export_job_sink = PrecomputedChunksSink(
                filesystem=scratch_fs_result,
                dtype=datasink.dtype,
                encoding=RawEncoder(),
                interval=datasink.interval,
                path=PurePosixPath("/raw_results/temp.precomputed"),
                resolution=(1,1,1),
                scale_key=PurePosixPath("temp_export"),
                tile_shape=datasink.tile_shape,
            )

            on_export_success: Callable[[DataSink], Any] = lambda export_sink: self._launch_create_dzi_pyramid_job(
                name="Creating DZI pyramid levels...",
                filesystem=scratch_fs_result,
                xml_path=scratch_fs_xml_path,
                dzi_image=datasink.dzi_image,
                num_channels=3,
                on_succcess=lambda pyramid: self._launch_convert_to_dzi_job(
                    datasource=export_job_sink.to_datasource(),
                    pyramid=pyramid,
                    on_succcess=lambda _: self._launch_job(
                        ZipDirectory(
                            name=f"Zipping results from {datasink.url.raw}...",
                            input_fs=pyramid[0].filesystem,
                            input_directory=scratch_fs_xml_path.parent,
                            output_fs=scratch_fs_result,
                            output_path=scratch_fs_dzip_path,
                            delete_source=True,
                        ),
                        on_success=lambda _: self._launch_job(
                            SimpleJob[None, Exception](
                                f"Transferring results to {datasink.filesystem.geturl(PurePosixPath('/'))}",
                                target=target_fs.transfer_file,
                                source_fs=scratch_fs_result,
                                source_path=scratch_fs_dzip_path,
                                target_path=target_dzip_path,
                            ),
                            clean_on_success=False,
                            on_success=lambda _: print(f"Should have transferred to {target_fs.geturl(target_dzip_path)}")
                        ),
                    ),
                )
            )
        else:
            export_job_sink = datasink
            on_export_success: Callable[[DataSink], Any] = lambda sink: None

        _ = self._launch_export_job(
            job_name="Exporting Simple Segmentation",
            datasource=datasource,
            operator=segmenter,
            datasink=export_job_sink,
            on_success=on_export_success,
        )


class WsPixelClassificationExportApplet(WsApplet, PixelClassificationExportApplet):
    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> "UsageError | None":
        if method_name == "launch_pixel_probabilities_export_job":
            params_result = StartPixelProbabilitiesExportJobParamsDto.from_json_value(arguments)
            if isinstance(params_result, MessageParsingError):
                return UsageError(str(params_result)) #FIXME: this is a bug, not a usage error
            datasource_result = FsDataSource.try_from_message(params_result.datasource)
            if isinstance(datasource_result, Exception):
                return UsageError(str(datasource_result)) #FIXME: this is a bug, not a usage error
            datasink_result = DataSink.create_from_message(params_result.datasink)
            if isinstance(datasink_result, Exception):
                return UsageError(str(datasink_result)) #FIXME: may not be an usage error
            rpc_result = self.launch_pixel_probabilities_export_job(
                datasource=datasource_result, datasink=datasink_result
            )
        elif method_name == "launch_simple_segmentation_export_job":
            params_result = StartSimpleSegmentationExportJobParamsDto.from_json_value(arguments)
            if isinstance(params_result, MessageParsingError):
                return UsageError(str(params_result)) #FIXME: this is a bug, not a usage error
            datasource_result = FsDataSource.try_from_message(params_result.datasource)
            if isinstance(datasource_result, Exception):
                return UsageError(str(datasource_result)) #FIXME: this is a bug, not a usage error
            datasink_result = DataSink.create_from_message(params_result.datasink)
            if isinstance(datasink_result, Exception):
                return UsageError(str(datasink_result)) #FIXME: may not be an usage error

            rpc_result = self.launch_simple_segmentation_export_job(datasource=datasource_result, datasink=datasink_result, label_name=params_result.label_header.name)
        else:
            raise ValueError(f"Invalid method name: '{method_name}'") #FIXME: return error
        return rpc_result

    def get_state_dto(self) -> PixelClassificationExportAppletStateDto:
        with self._lock:
            labels = self._in_populated_labels()
            datasource_suggestions = self._in_datasource_suggestions()
            return PixelClassificationExportAppletStateDto(
                jobs=tuple(job.to_dto() for job in self._jobs.values()),
                populated_labels=None if not labels else tuple(l.to_header_message() for l in labels),
                datasource_suggestions=None if datasource_suggestions is None else tuple(ds.to_dto() for ds in datasource_suggestions)
            )

    def _get_json_state(self) -> JsonValue:
        return self.get_state_dto().to_json_value()