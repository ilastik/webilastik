# pyright: strict

import threading
import time
from typing import Dict, Generic, Optional, Tuple, Union
import logging
import uuid
from ndstructs.array5D import Array5D

from ndstructs.utils.json_serializable import JsonObject, ensureJsonString

from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.features.ilp_filter import IlpFilter
from webilastik.operator import Operator, IN
from webilastik.scheduling.hashing_executor import HashingExecutor, Job, JobCompletedCallback, JobProgressCallback
from webilastik.ui.applet import AppletOutput, NoSnapshotApplet, PropagationOk, PropagationResult, UserPrompt
from webilastik.datasource import DataRoi, DataSource
from webilastik.datasink import DataSink
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError

logger = logging.getLogger(__name__)

class ExportTask(Generic[IN]):
    def __init__(self, operator: Operator[IN, Array5D], sink: DataSink):
        self.operator = operator
        self.sink = sink

    def __call__(self, step_arg: IN):
        tile = self.operator.compute(step_arg)
        self.sink.write(tile)


ClassifierOutput = AppletOutput[Optional[VigraPixelClassifier[IlpFilter]]]

class ExportApplet(NoSnapshotApplet):
    def __init__(
        self,
        *,
        name: str,
        executor: HashingExecutor,
        operator: AppletOutput[Optional[Operator[DataRoi, Array5D]]],
        datasource: AppletOutput[Optional[DataSource]],
        datasink: AppletOutput[Union[DataSink, UsageError, None]],
    ):
        self._in_operator = operator
        self._in_datasource = datasource
        self._in_datasink = datasink

        self._error_message: Optional[str] = None

        self.executor = executor
        super().__init__(name=name)

    def on_dependencies_changed(self, user_prompt: UserPrompt) -> PropagationResult:
        self._check_dependencies()
        return PropagationOk()

    def _check_dependencies(self):
        if self._in_operator() is None:
            self._error_message = "Upstream applet is not ready yet"
        elif self._in_datasource() is None:
            self._error_message = "No datasource selected"
        else:
            self._error_message = None

    def start_export_job(
        self,
        *,
        on_progress: Optional[JobProgressCallback] = None,
        on_complete: Optional[JobCompletedCallback] = None,
    ) -> Optional[Job[DataRoi]]:
        self._check_dependencies()
        operator = self._in_operator()
        datasource = self._in_datasource()
        if operator is None or datasource is None:
            return None
        sink_result = self._in_datasink()
        if sink_result is None:
            self._error_message = "No datasink selected"
            return None
        elif isinstance(sink_result, UsageError):
            self._error_message = f"Failed to create datasink: {sink_result}"
            return None

        job = Job(
            name="Pixel Classification Export", # FIXME
            target=ExportTask(operator=operator, sink=sink_result),
            args=datasource.roi.get_datasource_tiles(),
            on_progress=on_progress,
            on_complete=on_complete,
        )
        self.executor.submit_job(job)
        self._error_message = None
        return job


class WsExportApplet(WsApplet, ExportApplet):
    def __init__(
        self,
        *,
        name: str,
        executor: HashingExecutor,
        operator: AppletOutput[Optional[Operator[DataRoi, Array5D]]],
        datasource: AppletOutput[Optional[DataSource]],
        datasink: AppletOutput[Optional[DataSink]]
    ):
        self.jobs: Dict[uuid.UUID, Job[DataRoi]] = {}
        self.lock = threading.Lock()
        self.last_update = time.monotonic()
        super().__init__(name=name, executor=executor, operator=operator, datasource=datasource, datasink=datasink)

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        if method_name == "start_export_job":
            def on_job_step_completed(job_id: uuid.UUID, step_index: int):
                logger.debug(f"** Job step {job_id}:{step_index} done")
                self._mark_updated()

            def on_job_completed(job_id: uuid.UUID):
                logger.debug(f"**** Job {job_id} completed")
                self._mark_updated()

            job_result = self.start_export_job(
                on_progress=on_job_step_completed,
                on_complete=on_job_completed,
            )
            if job_result is None:
                return None
            self.jobs[job_result.uuid] = job_result

            logger.info(f"Started job {job_result.uuid}")
            return None

        if method_name == "cancel_job":
            job_id = uuid.UUID(ensureJsonString(arguments.get("job_id")))
            self.executor.cancel_group(job_id)
            _ = self.jobs.pop(job_id, None)
            return None
        raise ValueError(f"Invalid method name: '{method_name}'")

    def _mark_updated(self):
        with self.lock:
            self.last_update = time.monotonic()

    def get_updated_status(self, last_seen_update: float) -> Tuple[float, Optional[JsonObject]]:
        with self.lock:
            if last_seen_update < self.last_update:
                return (self.last_update, self._get_json_state())
            return (self.last_update, None)

    def _get_json_state(self) -> JsonObject:
        return {
            "jobs": tuple(job.to_json_value() for job in self.jobs.values()),
            "error_message": self._error_message,
        }