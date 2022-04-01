import threading
from typing import Any, Callable, Dict, Generic, Iterable, List, Sequence
from concurrent.futures import Executor, Future
import uuid

import numpy as np
from ndstructs.array5D import Array5D
from ndstructs.utils.json_serializable import JsonObject, ensureJsonArray

from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasink import DataSink, DataSinkWriter
from webilastik.datasource import DataRoi, DataSource
from webilastik.features.ilp_filter import IlpFilter
from webilastik.operator import IN, Operator
from webilastik.scheduling.job import Job, JobExecutor, IN as JOB_IN, OUT as JOB_OUT
from webilastik.simple_segmenter import SimpleSegmenter
from webilastik.ui.applet import AppletOutput, StatelesApplet, UserPrompt
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError

class ExportTask(Generic[IN]):
    def __init__(self, operator: Operator[IN, Array5D], sink_writer: DataSinkWriter):
        self.operator = operator
        self.sink_writer = sink_writer

    def __call__(self, step_arg: IN):
        tile = self.operator.compute(step_arg)
        self.sink_writer.write(tile)

class ExportAsSimpleSegmentationTask:
    def __init__(self, operator: Operator[DataRoi, Array5D], sink_writers: Sequence[DataSinkWriter]):
        self.operator = SimpleSegmenter(preprocessor=operator)
        self.sink_writers = sink_writers

    def __call__(self, step_arg: DataRoi):
        segmentations = self.operator.compute(step_arg)
        for segmentation, sink in zip(segmentations, self.sink_writers):
            sink.write(segmentation)

class PixelClassificationExportApplet(StatelesApplet):
    def __init__(
        self,
        *,
        name: str,
        on_async_change: Callable[[], Any],
        executor: Executor,
        job_executor: JobExecutor,
        operator: "AppletOutput[VigraPixelClassifier[IlpFilter] | None]",
    ):
        self.on_async_change = on_async_change
        self.executor = executor
        self.job_executor = job_executor

        self._in_operator = operator

        self._jobs: Dict[uuid.UUID, Job[Any, Any]] = {}
        self._lock = threading.Lock()
        super().__init__(name=name)

    def _remove_job(self, job_id: uuid.UUID):
        with self._lock:
            del self._jobs[job_id]

    def _create_job(
        self,
        *,
        name: str,
        target: Callable[[JOB_IN], JOB_OUT],
        args: Iterable[JOB_IN],
        num_args: "int | None" = None,
    ) -> Job[JOB_IN, JOB_OUT]:
        job = Job(
            name=name,
            target=target,
            on_progress=lambda job_id, step_index: self.on_async_change(),
            args=args,
            num_args=num_args
        )
        job.add_done_callback(lambda _: self.on_async_change())
        with self._lock:
            self._jobs[job.uuid] = job
        self.job_executor.submit(job)
        return job

    def start_export_job(self, *, datasource: DataSource, datasink: DataSink) -> "UsageError | None":
        classifier = self._in_operator()
        if classifier is None:
            return UsageError("Upstream not ready yet")
        expected_shape = datasource.shape.updated(c=classifier.num_classes)
        if datasink.shape != expected_shape:
            return UsageError(f"Bad sink shape. Expected {expected_shape} but got {datasink.shape}")
        if datasink.dtype != np.dtype("float32"):
            return UsageError("Data sink should have dtype of float32 for this kind of export")


        sink_creation_job = self._create_job(
            name=f"Creating datasink",
            target=lambda _: datasink.create(),
            args=[None],
        )
        sink_creation_job.add_done_callback(lambda _: self._remove_job(sink_creation_job.uuid))

        def launch_export_job(future_sink_writer: "Future[Exception | DataSinkWriter]"):
            result = future_sink_writer.result()
            if isinstance(result, Exception):
                raise result #FIXME?

            _ = self._create_job(
                name=f"Export Job",
                target=ExportTask(operator=classifier, sink_writer=result),
                args=datasource.roi.get_datasource_tiles(), #FIXME: use sink tile_size
            )
        sink_creation_job.add_done_callback(launch_export_job)

    def start_simple_segmentation_export_job(self, *, datasource: DataSource, datasinks: List[DataSink]) -> "UsageError | None":
        classifier = self._in_operator()
        if classifier is None:
            return UsageError("Upstream not ready yet")
        if len(datasinks) != classifier.num_classes:
            return UsageError(f"Wrong number of datasinks. Expected {classifier.num_classes} but got {len(datasinks)}")
        expected_shape = datasource.shape.updated(c=3)
        if any(sink.shape != expected_shape for sink in datasinks):
            return UsageError("All data sinks should have 3 channels for this kind of export")
        if any(sink.dtype != np.dtype("uint8") for sink in datasinks):
            return UsageError("All data sinks should have dtype of uint8 for this kind of export")

        def create_datasinks() -> "Exception | Sequence[DataSinkWriter]":
            out: List[DataSinkWriter] = []
            for sink in datasinks:
                result = sink.create()
                if isinstance(result, Exception):
                    raise result
                out.append(result)
            return out
        sink_creation_job = self._create_job(
            name=f"Creating datasinks",
            target=lambda _: create_datasinks(),
            args=[None],
        )
        sink_creation_job.add_done_callback(lambda _: self._remove_job(sink_creation_job.uuid))

        def launch_export_job(future_sink_writer: "Future[Exception | Sequence[DataSinkWriter]]"):
            result = future_sink_writer.result()
            if isinstance(result, Exception):
                raise result
            _ = self._create_job(
                name=f"Export Job",
                target=ExportAsSimpleSegmentationTask(operator=classifier, sink_writers=result),
                args=datasource.roi.get_datasource_tiles(), #FIXME: use sink tile_size
            )
        sink_creation_job.add_done_callback(launch_export_job)

class WsPixelClassificationExportApplet(WsApplet, PixelClassificationExportApplet):
    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> "UsageError | None":
        if method_name == "start_export_job":
            datasource = DataSource.from_json_value(arguments.get("datasource"))
            datasink = DataSink.from_json_value(arguments.get("datasink"))
            rpc_result = self.start_export_job(datasource=datasource, datasink=datasink)
        elif method_name == "start_simple_segmentation_export_job":
            datasource = DataSource.from_json_value(arguments.get("datasource"))
            datasinks = [DataSink.from_json_value(raw_sink) for raw_sink in ensureJsonArray(arguments.get("datasinks"))]
            rpc_result = self.start_simple_segmentation_export_job(datasource=datasource, datasinks=datasinks)
        else:
            raise ValueError(f"Invalid method name: '{method_name}'")
        return rpc_result

    def _get_json_state(self) -> JsonObject:
        with self._lock:
            classifier = self._in_operator()
            return {
                "jobs": tuple(job.to_json_value() for job in self._jobs.values()),
                "num_classes":  classifier and classifier.num_classes,
            }