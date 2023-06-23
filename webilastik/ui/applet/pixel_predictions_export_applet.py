# pyright: strict

from functools import partial
from pathlib import PurePosixPath
import threading
from typing import Any, Callable, Dict, Sequence, TypeVar, Union
import uuid

import numpy as np
from ndstructs.array5D import Array5D
from ndstructs.utils.json_serializable import JsonObject

from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasink import DataSink, IDataSinkWriter
from webilastik.datasink.deep_zoom_sink import DziLevelSink
from webilastik.datasource import DataRoi, DataSource, FsDataSource
from webilastik.datasource.deep_zoom_image import DziImageElement, DziSizeElement, ImageFormat
from webilastik.datasource.deep_zoom_datasource import DziLevelDataSource
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem import IFilesystem
from webilastik.filesystem.os_fs import OsFs
from webilastik.operator import OpRetriever, Operator
from webilastik.scheduling.job import JobStatus, PriorityExecutor
from webilastik.serialization.json_serialization import JsonValue
from webilastik.server.rpc.dto import (
    MessageParsingError,
    PixelClassificationExportAppletStateDto,
    StartPixelProbabilitiesExportJobParamsDto,
    StartSimpleSegmentationExportJobParamsDto,
)
from webilastik.simple_segmenter import SimpleSegmenter, SimpleSegmenterDataSource
from webilastik.ui.applet import AppletOutput, StatelesApplet, UserPrompt
from webilastik.ui.applet.export_jobs import CreateDziPyramid, DownscaleDatasource, ExportJob, OpenDatasinkJob, ZipDirectory
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError
from webilastik.ui.applet.brushing_applet import Label
from webilastik.utility import get_now_string

JOB_OUT = TypeVar("JOB_OUT")

ExportJobUnion = Union[ExportJob, OpenDatasinkJob, CreateDziPyramid, DownscaleDatasource, ZipDirectory]

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

        self._jobs: Dict[uuid.UUID, ExportJobUnion] = {}
        self._lock = threading.Lock()
        super().__init__(name=name)

    def _remove_job(self, job_id: uuid.UUID):
        with self._lock:
            del self._jobs[job_id]

    def _launch_job(self, job: ExportJobUnion):
        self.priority_executor.submit_job(job)
        with self._lock:
            self._jobs[job.uuid] = job
        self.on_async_change()

    def _launch_open_datasink_job(self, *, datasink: DataSink, on_complete: Callable[["IDataSinkWriter | Exception"], None]):
        def clean_datasink_job_then_run_on_complete(job_id: uuid.UUID, job_status: JobStatus, step_index: int, step_result: "IDataSinkWriter | Exception"):
            if not isinstance(step_result, Exception):
                self._remove_job(job_id)
            on_complete(step_result)

        self._launch_job(OpenDatasinkJob(
            datasink=datasink,
            on_complete=clean_datasink_job_then_run_on_complete,
        ))

    def _launch_export_job(
        self, *, job_name: str, operator: Operator[DataRoi, Array5D], datasource: DataSource, datasink: DataSink
    ):

        def on_datasink_ready(result: "Exception | IDataSinkWriter"):
            if isinstance(result, BaseException):
                raise result #FIXME?

            def on_progress(job_id: uuid.UUID, job_status: JobStatus, step_index: int, step_result: "None | Exception"):
                self.on_async_change()

            self._launch_job(ExportJob(
                name=job_name,
                on_progress=on_progress,
                operator=operator,
                sink_writer=result,
                args=datasource.roi.split(block_shape=result.data_sink.tile_shape.updated(c=datasource.shape.c)),
                num_args=datasource.roi.get_num_tiles(tile_shape=result.data_sink.tile_shape),
            ))

        _ = self._launch_open_datasink_job(
            datasink=datasink,
            on_complete=on_datasink_ready,
        )

    def _launch_convert_to_dzip_job(
        self,
        *,
        datasource: DataSource,
        output_fs: IFilesystem,
        output_path: PurePosixPath, #FIXME: use it to save final zip to
        dzi_image_format: ImageFormat,
    ) -> "None | UsageError":
        tmp_fs = OsFs.create_scratch_dir()
        if isinstance(tmp_fs, Exception):
            return UsageError(str(tmp_fs)) #FIXME: double check this exception
        tmp_xml_path = PurePosixPath("/tmp.dzi")

        dzi_image = DziImageElement(
            Format=dzi_image_format,
            Overlap=0,
            Size=DziSizeElement(Width=datasource.shape.x, Height=datasource.shape.y),
            TileSize=max(datasource.tile_shape.x, datasource.tile_shape.y),
        )

        def launch_zip_dzi_pyramid_job(job_id: uuid.UUID, job_status: JobStatus, step_index: int, step_result: Any):
            if job_status != "completed":
                self.on_async_change()
                return
            self._remove_job(job_id)
            self._launch_job(ZipDirectory(
                name="Zipping dzi",
                input_fs=tmp_fs,
                input_directory=tmp_xml_path.parent,
                output_fs=output_fs,
                output_path=output_path,
                delete_source=True,
            ))

        def launch_downscaling_job(
            sinks: Sequence[DziLevelSink], sink_index: int, job_id: uuid.UUID, job_status: JobStatus, step_index: int, step_result: Any
        ) -> "Exception | None":
            if job_status != "completed":
                self.on_async_change()
                return
            if 0 <= sink_index < dzi_image.max_level_index:
                self._remove_job(job_id)
            sink = sinks[sink_index]

            if sink_index == dzi_image.max_level_index:
                level_source = datasource
            else:
                level_source = DziLevelDataSource.try_load( #FIXME: opening the source should be done inside the job
                    filesystem=tmp_fs,
                    level_path=dzi_image.make_level_path(
                        xml_path=tmp_xml_path,
                        level_index=sink.level_index + 1
                    )
                )
                if isinstance(level_source, Exception):
                    print(f"Failed to open the previous level source!!!! This needs to be reported back to the user!!!")
                    return level_source
            self._launch_job(DownscaleDatasource(
                name=f"Downscaling to {sink.shape.x} x {sink.shape.y}{'' if sink.shape.z == 1 else ' ' + str(sink.shape.z)}",
                source=level_source,
                sink_writer=sink.open(),
                on_progress=launch_zip_dzi_pyramid_job if sink_index == 0 else partial(launch_downscaling_job, sinks=sinks, sink_index=sink_index - 1),
            ))

        def on_pyramid_ready__launch_first_export(job_id: uuid.UUID, result: "Sequence[DziLevelSink] | Exception"):
            if isinstance(result, Exception):
                return #FIXME?
            self._remove_job(job_id)
            return launch_downscaling_job(
                sinks=result,
                sink_index=dzi_image.max_level_index,
                job_id=job_id,
                job_status="completed",
                step_index=0,
                step_result=None,
            )

        self._launch_job(CreateDziPyramid(
            name="Creating dzi levels",
            filesystem=tmp_fs,
            dzi_image=DziImageElement(
                Format=dzi_image_format,
                Overlap=0,
                Size=DziSizeElement(
                    Width=datasource.shape.x,
                    Height=datasource.shape.y,
                ),
                TileSize=max(datasource.tile_shape.x, datasource.tile_shape.y),
            ),
            num_channels=3,
            xml_path=tmp_xml_path,
            on_complete=on_pyramid_ready__launch_first_export,
        ))

    def launch_pixel_probabilities_export_job(self, *, datasource: DataSource, datasink: DataSink) -> "UsageError | None":
        classifier = self._in_operator()
        if classifier is None:
            return UsageError("Upstream not ready yet")
        expected_shape = datasource.shape.updated(c=classifier.num_classes)
        if datasink.shape != expected_shape:
            return UsageError(f"Bad sink shape. Expected {expected_shape} but got {datasink.shape}")
        if datasink.dtype != np.dtype("float32"):
            return UsageError("Data sink should have dtype of float32 for this kind of export")
        return self._launch_export_job(job_name="Exporting Pixel Probabilities", operator=classifier, datasource=datasource, datasink=datasink)


    def create_simple_segmenter_datasource(self, *, datasource: DataSource, label_name: str) -> "SimpleSegmenterDataSource | UsageError":
        with self._lock:
            label_name_indices: Dict[str, int] = {label.name: idx for idx, label in enumerate(self._in_populated_labels() or [])}
            classifier = self._in_operator()
        if label_name not in label_name_indices:
            return UsageError(f"Bad label name: {label_name}")
        if classifier is None:
            return UsageError("Applets upstream are not ready yet")
        if not classifier.is_applicable_to(datasource):
            return UsageError(f"Classifier is not compatible with provided datasource: {datasource}")
        return SimpleSegmenterDataSource(
            upstream_source=datasource,
            segmenter=SimpleSegmenter(
                preprocessor=classifier,
                channel_index=label_name_indices[label_name],
            ),
        )

    def launch_simple_segmentation_export_job(self, *, datasource: DataSource, datasink: DataSink, label_name: str) -> "UsageError | None":
        simple_segmentation_datasource = self.create_simple_segmenter_datasource(datasource=datasource, label_name=label_name)
        if isinstance(simple_segmentation_datasource, UsageError):
            return simple_segmentation_datasource
        expected_shape = datasource.shape.updated(c=3)
        if datasink.shape != expected_shape:
            return UsageError("Data sink should have 3 channels for this kind of export")
        if datasink.dtype != np.dtype("uint8"):
            return UsageError("Data sink should have dtype of 'uint8' for this kind of export")

        if isinstance(datasink, DziLevelSink):
            #FIXME? The function signature suggests that one could write to a single Dzi level, uncompressed even.
            #       But we are always producing a .dzip
            return self._launch_convert_to_dzip_job(
                output_fs=datasink.filesystem,
                output_path=datasink.xml_path,
                datasource=simple_segmentation_datasource,
                dzi_image_format=datasink.dzi_image.Format,
            )

        return self._launch_export_job(
            job_name="Exporting Simple Segmentation",
            operator=OpRetriever(),
            datasource=simple_segmentation_datasource,
            datasink=datasink,
        )

    def launch_convert_to_dzip_job(
        self,
        *,
        datasource: DataSource,
        output_fs: IFilesystem,
        output_path: PurePosixPath,
        dzi_image_format: ImageFormat,
    ) -> "UsageError | None":
        return self._launch_convert_to_dzip_job(
            output_fs=output_fs,
            output_path=output_path,
            datasource=datasource,
            dzi_image_format=dzi_image_format,
        )

    def launch_export_simple_segmentation_to_dzip(
        self,
        *,
        datasource: DataSource,
        output_fs: IFilesystem,
        output_path: PurePosixPath,
        dzi_image_format: ImageFormat,
        label_name: str,
    ) -> "UsageError | None":
        simple_segmentation_datasource = self.create_simple_segmenter_datasource(datasource=datasource, label_name=label_name)
        if isinstance(simple_segmentation_datasource, UsageError):
            return simple_segmentation_datasource
        return self._launch_convert_to_dzip_job(
            output_fs=output_fs,
            output_path=output_path,
            datasource=simple_segmentation_datasource,
            dzi_image_format=dzi_image_format,
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