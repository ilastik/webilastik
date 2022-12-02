# pyright: strict

from dataclasses import dataclass
import threading
from typing import Any, Callable, Dict, Generic, Iterable, Sequence
import uuid

import numpy as np
from ndstructs.array5D import Array5D
from ndstructs.utils.json_serializable import JsonObject

from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasink import DataSink, IDataSinkWriter
from webilastik.datasource import DataRoi, DataSource, FsDataSource
from webilastik.features.ilp_filter import IlpFilter
from webilastik.operator import IN, Operator
from webilastik.scheduling.job import Job, JobSucceededCallback, PriorityExecutor
from webilastik.serialization.json_serialization import JsonValue
from webilastik.server.rpc.dto import (
    MessageParsingError,
    PixelClassificationExportAppletStateDto,
    StartPixelProbabilitiesExportJobParamsDto,
    StartSimpleSegmentationExportJobParamsDto,
    ExportJobDto,
)
from webilastik.simple_segmenter import SimpleSegmenter
from webilastik.ui.applet import AppletOutput, StatelesApplet, UserPrompt
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError
from webilastik.ui.applet.brushing_applet import Label

@dataclass
class _ExportTask(Generic[IN]):
    operator: Operator[IN, Array5D]
    sink_writer: IDataSinkWriter

    def __call__(self, step_arg: IN):
        tile = self.operator(step_arg)
        print(f"Writing tile {tile}")
        self.sink_writer.write(tile)


# this needs to be top-level becase process pools can't handle local functions
def _open_datasink(ds: DataSink) -> "IDataSinkWriter | Exception":
    return ds.open()


class _ExportJob(Job[DataRoi, None]):
    def __init__(
        self,
        *,
        name: str,
        on_changed: Callable[[], None],
        operator: Operator[DataRoi, Array5D],
        sink_writer: IDataSinkWriter,
        args: Iterable[DataRoi],
        num_args: "int | None" = None,
    ):
        super().__init__(
            name=name,
            target=_ExportTask(operator=operator, sink_writer=sink_writer),
            on_progress=lambda job_id, step_index: on_changed(),
            on_success=lambda job_id, result: on_changed(),
            on_failure=lambda exception: on_changed(),
            args=args,
            num_args=num_args
        )
        self.sink_writer = sink_writer

    def to_dto(self) -> ExportJobDto:
        error_message: "str | None" = None
        with self.job_lock:
            return ExportJobDto(
                name=self.name,
                num_args=self.num_args,
                uuid=str(self.uuid),
                status=self._status,
                num_completed_steps=self.num_completed_steps,
                error_message=error_message,
                datasink=self.sink_writer.data_sink.to_dto()
            )

class _OpenDatasinkJob(Job[DataSink, "IDataSinkWriter | Exception"]):
    def __init__(
        self,
        *,
        on_complete: JobSucceededCallback["IDataSinkWriter | Exception"],
        datasink: DataSink,
    ):
        super().__init__(
            name="Creating datasink",
            target=_open_datasink,
            on_success=on_complete,
            args=[datasink],
            num_args=1
        )
        self.datasink = datasink

    def to_dto(self) -> ExportJobDto:
        error_message: "str | None" = None
        with self.job_lock:
            return ExportJobDto(
                name=self.name,
                num_args=self.num_args,
                uuid=str(self.uuid),
                status=self._status,
                num_completed_steps=self.num_completed_steps,
                error_message=error_message,
                datasink=self.datasink.to_dto()
            )

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

        self._jobs: Dict[uuid.UUID, "_ExportJob | _OpenDatasinkJob"] = {}
        self._lock = threading.Lock()
        super().__init__(name=name)

    def _remove_job(self, job_id: uuid.UUID):
        with self._lock:
            del self._jobs[job_id]

    def _launch_job(self, job: "_ExportJob | _OpenDatasinkJob"):
        self.priority_executor.submit_job(job)
        with self._lock:
            self._jobs[job.uuid] = job

    def _launch_open_datasink_job(self, *, datasink: DataSink, on_complete: Callable[["IDataSinkWriter | Exception"], None]):
        def clean_datasink_job_then_run_on_complete(job_id: uuid.UUID, result: "IDataSinkWriter | Exception"):
            if not isinstance(result, Exception):
                self._remove_job(job_id)
            on_complete(result)

        self._launch_job(_OpenDatasinkJob(
            datasink=datasink,
            on_complete=clean_datasink_job_then_run_on_complete,
        ))

    def _launch_export_job(
        self, *, job_name: str, operator: Operator[DataRoi, Array5D], datasource: DataSource, datasink: DataSink
    ):

        def on_datasink_ready(result: "Exception | IDataSinkWriter"):
            if isinstance(result, BaseException):
                raise result #FIXME?
            self._launch_job(_ExportJob(
                name=job_name,
                on_changed=self.on_async_change,
                operator=operator,
                sink_writer=result,
                args=datasource.roi.get_datasource_tiles(), #FIXME: use sink tile_size
                num_args=datasource.roi.get_num_tiles(tile_shape=datasource.tile_shape),
            ))

        _ = self._launch_open_datasink_job(
            datasink=datasink,
            on_complete=on_datasink_ready,
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
        return self._launch_export_job(job_name="Exporting Pixel Probabilities", operator=classifier, datasource=datasource, datasink=datasink)

    def launch_simple_segmentation_export_job(self, *, datasource: DataSource, datasink: DataSink, label_name: str) -> "UsageError | None":
        with self._lock:
            label_name_indices: Dict[str, int] = {label.name: idx for idx, label in enumerate(self._in_populated_labels() or [])}
            classifier = self._in_operator()
        if label_name not in label_name_indices:
            return UsageError(f"Bad label name: {label_name}")
        if classifier is None:
            return UsageError("Applets upstream are not ready yet")
        expected_shape = datasource.shape.updated(c=3)
        if datasink.shape != expected_shape:
            return UsageError("Data sink should have 3 channels for this kind of export")
        if datasink.dtype != np.dtype("uint8"):
            return UsageError("Data sink should have dtype of 'uint8' for this kind of export")
        return self._launch_export_job(
            job_name="Exporting Simple Segmentation",
            operator=SimpleSegmenter(channel_index=label_name_indices[label_name], preprocessor=classifier),
            datasource=datasource,
            datasink=datasink,
        )


class WsPixelClassificationExportApplet(WsApplet, PixelClassificationExportApplet):
    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> "UsageError | None":
        if method_name == "launch_pixel_probabilities_export_job":
            params_result = StartPixelProbabilitiesExportJobParamsDto.from_json_value(arguments)
            if isinstance(params_result, MessageParsingError):
                return UsageError(str(params_result)) #FIXME: this is a bug, not a usage error
            datasource_result = FsDataSource.try_from_message(params_result.datasource)
            if isinstance(datasource_result, MessageParsingError):
                return UsageError(str(datasource_result)) #FIXME: this is a bug, not a usage error
            rpc_result = self.launch_pixel_probabilities_export_job(
                datasource=datasource_result, datasink=DataSink.create_from_message(params_result.datasink)
            )
        elif method_name == "launch_simple_segmentation_export_job":
            params_result = StartSimpleSegmentationExportJobParamsDto.from_json_value(arguments)
            if isinstance(params_result, MessageParsingError):
                return UsageError(str(params_result)) #FIXME: this is a bug, not a usage error
            datasource_result = FsDataSource.try_from_message(params_result.datasource)
            if isinstance(datasource_result, MessageParsingError):
                return UsageError(str(datasource_result)) #FIXME: this is a bug, not a usage error
            datasink = DataSink.create_from_message(params_result.datasink)
            rpc_result = self.launch_simple_segmentation_export_job(datasource=datasource_result, datasink=datasink, label_name=params_result.label_header.name)
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