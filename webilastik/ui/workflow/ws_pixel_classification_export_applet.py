# pyright: strict

import uuid
import time
import threading
from typing import Dict, Optional, Tuple
from ndstructs.utils.json_serializable import JsonObject, ensureJsonString
from webilastik.ui import parse_url
from webilastik.ui.applet import AppletOutput, UserPrompt
import logging


from webilastik.ui.applet.datasource_batch_processing_applet import PixelClasificationExportingApplet, PixelClassificationExportJob
from webilastik.ui.datasink import DataSinkCreationParams
from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.scheduling.hashing_executor import HashingExecutor
from webilastik.ui.usage_error import UsageError
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.libebrains.user_token import UserToken
from webilastik.features.ilp_filter import IlpFilter

logger = logging.getLogger(__name__)


class WsPixelClassificationExportApplet(WsApplet, PixelClasificationExportingApplet):
    def __init__(
        self,
        *,
        name: str,
        executor: HashingExecutor,
        pixel_classifier: AppletOutput[Optional[VigraPixelClassifier[IlpFilter]]],
        ebrains_user_token: UserToken,
    ):
        self.jobs: Dict[uuid.UUID, PixelClassificationExportJob] = {}
        self.ebrains_user_token = ebrains_user_token
        self.lock = threading.Lock()
        self.last_update = time.monotonic()
        super().__init__(name=name, executor=executor, classifier=pixel_classifier)

    def run_rpc__start_export_job(self, arguments: JsonObject) -> Optional[UsageError]:
        source_url = parse_url(ensureJsonString(arguments.get("source")))
        if isinstance(source_url, UsageError):
            return source_url

        sink_params = DataSinkCreationParams.from_json_value(arguments.get("sink_params"))
        if isinstance(sink_params, UsageError):
            return sink_params

        def on_job_step_completed(job_id: uuid.UUID, step_index: int):
            logger.debug(f"** Job step {job_id}:{step_index} done")
            self._mark_updated()

        def on_job_completed(job_id: uuid.UUID):
            logger.debug(f"**** Job {job_id} completed")
            self._mark_updated()

        job = self.start_export_job(
            source_url=source_url,
            sink_params=sink_params,
            on_progress=on_job_step_completed,
            on_complete=on_job_completed,
        )
        if isinstance(job, UsageError):
            return job
        self.jobs[job.uuid] = job

        logger.info(f"Started job {job.uuid}")
        return None

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        if method_name == "start_export_job":
            return self.run_rpc__start_export_job(arguments)
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
            "jobs": tuple(job.to_json_value() for job in self.jobs.values())
        }
