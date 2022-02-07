# pyright: strict

import enum
import threading
import time
from typing import Dict, Generic, Optional, Sequence, Tuple
import logging
import uuid
from ndstructs.array5D import Array5D
from pathlib import PurePosixPath, Path

from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonIntTripplet, ensureJsonString, ensureOptional, toJsonValue
import numpy as np

from webilastik.classifiers.pixel_classifier import PixelClassifier, VigraPixelClassifier
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksEncoder, PrecomputedChunksInfo, PrecomputedChunksScale, RawEncoder
from webilastik.features.ilp_filter import IlpFilter
from webilastik.libebrains.user_token import UserToken
from webilastik.operator import Operator, IN
from webilastik.scheduling.hashing_executor import HashingExecutor, Job, JobCompletedCallback, JobProgressCallback
from webilastik.simple_segmenter import SimpleSegmenter
from webilastik.ui.applet import AppletOutput, NoSnapshotApplet, PropagationError, PropagationOk, PropagationResult, UserPrompt, user_interaction
from webilastik.datasource import DataRoi, DataSource
from webilastik.datasink import DataSink
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError
from webilastik.utility import get_now_string
from webilastik.filesystem.bucket_fs import BucketFs
from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksSink

logger = logging.getLogger(__name__)

class ExportTask(Generic[IN]):
    def __init__(self, operator: Operator[IN, Array5D], sink: DataSink):
        self.operator = operator
        self.sink = sink

    def __call__(self, step_arg: IN):
        tile = self.operator.compute(step_arg)
        self.sink.write(tile)


class ExportAsSimpleSegmentationTask:
    def __init__(self, operator: Operator[DataRoi, Array5D], sinks: Sequence[DataSink]):
        self.operator = SimpleSegmenter(preprocessor=operator)
        self.sinks = sinks

    def __call__(self, step_arg: DataRoi):
        tile = self.operator.compute(step_arg)
        for channel_index, channel in enumerate(tile.split(tile.shape.updated(c=1))):
            self.sinks[channel_index].write(channel)

class ExportMode(enum.Enum):
    PREDICTIONS = "PREDICTIONS"
    SIMPLE_SEGMENTATION = "SIMPLE_SEGMENTATION"

    @staticmethod
    def from_json_value(value: JsonValue) -> "ExportMode":
        value_str = ensureJsonString(value)
        if value_str == ExportMode.PREDICTIONS.value:
            return ExportMode.PREDICTIONS
        if value_str == ExportMode.SIMPLE_SEGMENTATION.value:
            return ExportMode.SIMPLE_SEGMENTATION
        raise ValueError(f"Bad export mode: {value_str}")

    def to_json_value(self) -> str:
        return self.value

ClassifierOutput = AppletOutput[Optional[VigraPixelClassifier[IlpFilter]]]

class ExportApplet(NoSnapshotApplet):
    def __init__(
        self,
        *,
        name: str,
        ebrains_user_token: UserToken,
        executor: HashingExecutor,
        operator: AppletOutput[Optional[Operator[DataRoi, Array5D]]],
        datasource: AppletOutput[Optional[DataSource]],
    ):
        self.ebrains_user_token = ebrains_user_token

        self._in_operator = operator
        self._in_datasource = datasource

        self._sink_bucket_name: Optional[str] = "hbp-image-service"
        self._sink_prefix: Optional[PurePosixPath] = PurePosixPath(f"/webilastik_job_{get_now_string()}.precomputed")
        self._sink_voxel_offset: Tuple[int, int, int] = (0,0,0)
        self._sink_encoder: PrecomputedChunksEncoder = RawEncoder()

        self._error_message: Optional[str] = None
        self._mode = ExportMode.PREDICTIONS

        self.executor = executor
        super().__init__(name=name)

    def on_dependencies_changed(self, user_prompt: UserPrompt) -> PropagationResult:
        return PropagationOk()

    @user_interaction(refresh_self=True)
    def set_sink_params(
        self,
        user_prompt: UserPrompt,
        mode: Optional[ExportMode] = None,
        bucket_name: Optional[str] = None,
        prefix: Optional[PurePosixPath] = None,
        voxel_offset: Optional[Tuple[int, int, int]] = None,
        encoder: Optional[PrecomputedChunksEncoder] = RawEncoder(),
    ) -> PropagationResult:
        self._mode = mode or self._mode
        self._sink_bucket_name = bucket_name
        self._sink_prefix = prefix
        self._sink_voxel_offset = voxel_offset or self._sink_voxel_offset
        self._sink_encoder = encoder or self._sink_encoder
        return PropagationOk()

    def start_export_job(
        self,
        *,
        on_progress: Optional[JobProgressCallback] = None,
        on_complete: Optional[JobCompletedCallback] = None,
    ) -> Optional[Job[DataRoi]]:
        operator = self._in_operator()
        if operator is None:
            self._error_message = "Upstream applet is not ready yet"
            return None
        source = self._in_datasource()
        if source is None:
            self._error_message = "No datasource selected"
            return None
        if not self._sink_bucket_name:
            self._error_message = "Missing a bucket name"
            return None
        if not self._sink_prefix:
            self._error_message = "Missing a path (prefix) inside the bucket"
            return None

        classifier: PixelClassifier = operator #type: ignore
        filesystem = BucketFs(
            bucket_name=self._sink_bucket_name,
            prefix=PurePosixPath("/"),
            ebrains_user_token=self.ebrains_user_token,
        )

        if self._mode == ExportMode.PREDICTIONS:
            sink = PrecomputedChunksSink.create(
                base_path=Path(self._sink_prefix), #FIXME
                filesystem=filesystem,
                info=PrecomputedChunksInfo(
                    data_type=np.dtype("float32"), #FIXME? maybe operator.expected_dtype or smth?
                    type_="image",
                    num_channels=classifier.num_classes,
                    scales=tuple([
                        PrecomputedChunksScale(
                            key=Path("exported_data"),
                            size=(source.shape.x, source.shape.y, source.shape.z),
                            chunk_sizes=tuple([(source.tile_shape.x, source.tile_shape.y, source.tile_shape.z)]),
                            encoding=self._sink_encoder,
                            voxel_offset=self._sink_voxel_offset,
                            resolution=source.spatial_resolution
                        )
                    ]),
                )
            ).scale_sinks[0]
            job_target = ExportTask(operator=operator, sink=sink)
            job_name = "Pixel Predictions Export"
        else:
            sinks = [
                PrecomputedChunksSink.create(
                    base_path=Path(self._sink_prefix).joinpath(f"class_{pixel_class}"), #FIXME
                    filesystem=filesystem,
                    info=PrecomputedChunksInfo(
                        data_type=np.dtype("uint8"), #FIXME?
                        type_="image",
                        num_channels=1,
                        scales=tuple([
                            PrecomputedChunksScale(
                                key=Path("exported_data"),
                                size=(source.shape.x, source.shape.y, source.shape.z),
                                chunk_sizes=tuple([(source.tile_shape.x, source.tile_shape.y, source.tile_shape.z)]),
                                encoding=self._sink_encoder,
                                voxel_offset=self._sink_voxel_offset,
                                resolution=source.spatial_resolution
                            )
                        ]),
                    )
                ).scale_sinks[0]
                for pixel_class in range(classifier.num_classes)
            ]
            job_target = ExportAsSimpleSegmentationTask(operator=operator, sinks=sinks)
            job_name = "Simple Segmentation Export"

        job = Job(
            name=job_name, # FIXME: add datasource url?
            target=job_target,
            args=source.roi.get_datasource_tiles(),
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
        ebrains_user_token: UserToken,
        executor: HashingExecutor,
        operator: AppletOutput[Optional[Operator[DataRoi, Array5D]]],
        datasource: AppletOutput[Optional[DataSource]],
    ):
        self.jobs: Dict[uuid.UUID, Job[DataRoi]] = {}
        self.lock = threading.Lock()
        self.last_update = time.monotonic()
        super().__init__(
            name=name, executor=executor, operator=operator, datasource=datasource, ebrains_user_token=ebrains_user_token
        )

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        if method_name == "set_sink_params":
            bucket_name = ensureOptional(ensureJsonString, arguments.get("sink_bucket_name"))
            prefix = ensureOptional(ensureJsonString, arguments.get("sink_prefix"))
            voxel_offset = ensureOptional(ensureJsonIntTripplet, arguments.get("sink_voxel_offset"))
            encoder = ensureOptional(PrecomputedChunksEncoder.from_json_value, arguments.get("sink_encoder"))
            mode = ensureOptional(ExportMode.from_json_value, arguments.get("mode"))
            rpc_result = self.set_sink_params(
                user_prompt=user_prompt,
                bucket_name=bucket_name,
                prefix=PurePosixPath(prefix) if prefix else None,
                voxel_offset=voxel_offset,
                encoder=encoder,
                mode=mode,
            )
            if isinstance(rpc_result, PropagationError):
                return UsageError(rpc_result.message)
            return None

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
            "sink_bucket_name": toJsonValue(self._sink_bucket_name),
            "sink_prefix": toJsonValue(self._sink_prefix and str(self._sink_prefix)),
            "sink_voxel_offset": toJsonValue(self._sink_voxel_offset),
            "sink_encoder": toJsonValue(self._sink_encoder),
            "mode": self._mode.to_json_value(),
        }