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
from webilastik.ui.applet import AppletOutput, InertApplet, NoSnapshotApplet, UserPrompt
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

class PixelClasificationExportingApplet(NoSnapshotApplet, InertApplet):
    def __init__(
        self,
        *,
        name: str,
        executor: HashingExecutor,
        classifier: ClassifierOutput,
        datasource: AppletOutput[Optional[DataSource]],
        datasink: AppletOutput[Optional[DataSink]],
    ):
        self._in_classifier = classifier
        self._in_datasource = datasource
        self._in_datasink = datasink
        self.executor = executor
        super().__init__(name=name)

    def start_export_job(
        self,
        *,
        on_progress: Optional[JobProgressCallback] = None,
        on_complete: Optional[JobCompletedCallback] = None,
    ) -> Union[Job[DataRoi], UsageError]:
        classifier = self._in_classifier()
        if classifier is None:
            return UsageError("Classifier not ready yet")
        datasource = self._in_datasource()
        if datasource is None:
            return UsageError("No datasource selected")
        datasink = self._in_datasink()
        if datasink is None:
            return UsageError("No datasink selected")

        job = Job(
            name="Pixel Classification Export", # FIXME
            target=ExportTask(operator=classifier, sink=datasink),
            args=datasource.roi.get_datasource_tiles(),
            on_progress=on_progress,
            on_complete=on_complete,
        )
        self.executor.submit_job(job)
        return job


class WsPixelClassificationExportApplet(WsApplet, PixelClasificationExportingApplet):
    def __init__(
        self,
        *,
        name: str,
        executor: HashingExecutor,
        classifier: ClassifierOutput,
        datasource: AppletOutput[Optional[DataSource]],
        datasink: AppletOutput[Optional[DataSink]]
    ):
        self.jobs: Dict[uuid.UUID, Job[DataRoi]] = {}
        self.lock = threading.Lock()
        self.last_update = time.monotonic()
        super().__init__(name=name, executor=executor, classifier=classifier, datasource=datasource, datasink=datasink)

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
            if isinstance(job_result, UsageError):
                return job_result
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
        }