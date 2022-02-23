# pyright: strict

import enum
import threading
import time
from typing import Any, Callable, Dict, Generic, List, Literal, Optional, Sequence, Tuple, TypeVar
import logging
import uuid
from ndstructs.array5D import Array5D
from pathlib import PurePosixPath, Path
from dataclasses import dataclass
from concurrent.futures import Future

from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonIntTripplet, ensureJsonString
import numpy as np

from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksEncoder, PrecomputedChunksInfo, PrecomputedChunksScale, RawEncoder
from webilastik.features.ilp_filter import IlpFilter
from webilastik.operator import Operator, IN
from webilastik.scheduling.hashing_executor import HashingExecutor, Job, JobCompletedCallback, JobProgressCallback
from webilastik.simple_segmenter import SimpleSegmenter
from webilastik.ui.applet import AppletOutput, NoSnapshotApplet, PropagationError, PropagationOk, PropagationResult, UserPrompt, user_interaction
from webilastik.datasource import DataRoi, DataSource
from webilastik.datasink import DataSink
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError
from webilastik.utility import Absent, get_now_string
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
        segmentations = self.operator.compute(step_arg)
        for segmentation, sink in zip(segmentations, self.sinks):
            sink.write(segmentation)

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
RoiOperator = Operator[DataRoi, Array5D]



@dataclass
class _State:
    operator: "RoiOperator | None"
    datasource: "DataSource | None"
    sink_bucket_name: "str | None" = "hbp-image-service"
    sink_prefix: "PurePosixPath | None" = PurePosixPath(f"/webilastik_job_{get_now_string()}.precomputed")
    sink_voxel_offset: Tuple[int, int, int] = (0,0,0)
    sink_encoder: PrecomputedChunksEncoder = RawEncoder()
    mode: ExportMode = ExportMode.PREDICTIONS

    def updated_with(
        self,
        *,
        operator: "RoiOperator | None | Absent" = Absent(),
        datasource: "DataSource | None | Absent" = Absent(),
        sink_bucket_name: "str | None | Absent" = Absent(),
        sink_prefix: "PurePosixPath | None | Absent" = Absent(),
        sink_voxel_offset: "Tuple[int, int, int] | Absent" = Absent(),
        sink_encoder: "PrecomputedChunksEncoder | Absent" = Absent(),
        mode: "ExportMode | Absent" = Absent(),
    ) -> "_State":
        return _State(
            operator=Absent.coalesce(operator, default=self.operator),
            datasource=Absent.coalesce(datasource, default=self.datasource),
            sink_bucket_name=Absent.coalesce(sink_bucket_name, default=self.sink_bucket_name),
            sink_prefix=Absent.coalesce(sink_prefix, self.sink_prefix),
            sink_voxel_offset=Absent.coalesce(sink_voxel_offset, default=self.sink_voxel_offset),
            sink_encoder=Absent.coalesce(sink_encoder, default=self.sink_encoder),
            mode=Absent.coalesce(mode, default=self.mode)
        )

    def get_status_description(self) -> Literal["upstream not ready", "no datasource selected", "missing bucket name", "missing bucket prefix", "ready"]:
        if self.operator is None:
            return "upstream not ready"
        if self.datasource is None:
            return "no datasource selected"
        if not self.sink_bucket_name:
            return "missing bucket name"
        if not self.sink_prefix:
            return "missing bucket prefix"
        return "ready"

    def to_json_value(self) -> JsonObject:
        return {
            "sink_bucket_name": self.sink_bucket_name,
            "sink_prefix": self.sink_prefix and str(self.sink_prefix),
            "sink_voxel_offset": self.sink_voxel_offset,
            "sink_encoder": self.sink_encoder.to_json_value(),
            "mode": self.mode.to_json_value(),
            "status_description": self.get_status_description(),
        }

    # FIXME
    def try_to_data_sinks(self, _: None) -> "Sequence[DataSink] | UsageError":
        datasource = self.datasource
        classifier: VigraPixelClassifier[IlpFilter] = self.operator #type: ignore
        sink_prefix = self.sink_prefix
        sink_bucket_name = self.sink_bucket_name

        if datasource is None:
            return UsageError("Missing data source")
        if classifier is None:
            return UsageError("Upstream not ready yet")
        if not sink_prefix:
            return UsageError("Missing sink prefix")
        if not sink_bucket_name:
            return UsageError("Missing bucket name")

        filesystem_result = BucketFs.try_create(
            bucket_name=sink_bucket_name,
            prefix=PurePosixPath("/"),
        )
        if isinstance(filesystem_result, UsageError):
            return filesystem_result

        if self.mode == ExportMode.PREDICTIONS:
            return PrecomputedChunksSink.create(
                base_path=Path(sink_prefix),
                filesystem=filesystem_result,
                info=PrecomputedChunksInfo(
                    data_type=np.dtype("float32"),
                    type_="image",
                    num_channels=classifier.num_classes,
                    scales=tuple([
                        PrecomputedChunksScale(
                            key=Path("exported_data"),
                            size=(datasource.shape.x, datasource.shape.y, datasource.shape.z),
                            chunk_sizes=tuple([(datasource.tile_shape.x, datasource.tile_shape.y, datasource.tile_shape.z)]),
                            encoding=self.sink_encoder,
                            voxel_offset=self.sink_voxel_offset,
                            resolution=datasource.spatial_resolution
                        )
                    ]),
                )
            ).scale_sinks
        elif self.mode == ExportMode.SIMPLE_SEGMENTATION:
            return [
                PrecomputedChunksSink.create(
                    base_path=Path(sink_prefix).joinpath(f"class_{pixel_class}"),
                    filesystem=filesystem_result,
                    info=PrecomputedChunksInfo(
                        data_type=np.dtype("uint8"),
                        type_="image",
                        num_channels=3,
                        scales=tuple([
                            PrecomputedChunksScale(
                                key=Path("exported_data"),
                                size=(datasource.shape.x, datasource.shape.y, datasource.shape.z),
                                chunk_sizes=tuple([(datasource.tile_shape.x, datasource.tile_shape.y, datasource.tile_shape.z)]),
                                encoding=self.sink_encoder,
                                voxel_offset=self.sink_voxel_offset,
                                resolution=datasource.spatial_resolution
                            )
                        ]),
                    )
                ).scale_sinks[0]
                for pixel_class in range(classifier.num_classes)
            ]
        else:
            raise NotImplementedError(f"{self.mode} is not implemented")



T = TypeVar("T", covariant=True)

class JsonableFuture(Generic[T]):
    def __init__(self, name: str, future: Future[T]) -> None:
        self.name = name
        self.future = future

    @property
    def status(self) -> Literal["success", "failed", "running"]:
        # FIXME: pending?
        if not self.future.done():
            return "running"
        exception = self.future.exception()
        if exception:
            return "failed"
        else:
            return "success"

    def to_json_value(self) -> JsonObject:
        return {
            "name": self.name,
            "status": self.status,
        }

Interaction = Callable[[], Optional[UsageError]]

class ExportApplet(NoSnapshotApplet):
    def __init__(
        self,
        *,
        name: str,
        enqueue_interaction: Callable[[Interaction], Any],
        executor: HashingExecutor,
        operator: AppletOutput[Optional[RoiOperator]],
        datasource: AppletOutput[Optional[DataSource]],
    ):
        self._in_operator = operator
        self._in_datasource = datasource
        self.executor = executor

        self._state: _State = _State(operator=None, datasource=None)
        self._lock = threading.Lock()
        self._jobs: Dict[uuid.UUID, Job[DataRoi]] = {}
        self._sink_creation_tasks: "List[  JsonableFuture[ Sequence[DataSink]|UsageError ]  ]" = []
        self._enqueue_interaction = enqueue_interaction

        super().__init__(name=name)

    def on_dependencies_changed(self, user_prompt: UserPrompt) -> PropagationResult:
        self._state = self._state.updated_with(operator=self._in_operator(), datasource=self._in_datasource())
        return PropagationOk()

    @user_interaction(refresh_self=True)
    def set_sink_params(
        self,
        user_prompt: UserPrompt,
        sink_bucket_name: "str | None | Absent" = Absent(),
        sink_prefix: "PurePosixPath | None | Absent" = Absent(),
        sink_voxel_offset: "Tuple[int, int, int] | Absent" = Absent(),
        sink_encoder: "PrecomputedChunksEncoder | Absent" = Absent(),
        mode: "ExportMode | Absent" = Absent(),
    ) -> PropagationResult:
        self._state = self._state.updated_with(
            sink_bucket_name=sink_bucket_name,
            sink_prefix=sink_prefix,
            sink_voxel_offset=sink_voxel_offset,
            sink_encoder=sink_encoder,
            mode=mode,
        )
        return PropagationOk()

    def start_export_job(
        self,
        *,
        on_progress: Optional[JobProgressCallback] = None,
        on_complete: Optional[JobCompletedCallback] = None,
    ) -> "UsageError | None":
        state = self._state
        datasource = state.datasource
        classifier: VigraPixelClassifier[IlpFilter] = state.operator #type: ignore #FIXME: make _State generic

        if datasource is None:
            return UsageError("Missing data source")
        if classifier is None:
            return UsageError("Upstream not ready yet")

        future_sinks = JsonableFuture(
            name="Creating data sinks",
            future=self.executor.submit(state.try_to_data_sinks, None) #FIXME
        )
        with self._lock:
            self._sink_creation_tasks.append(future_sinks)

        def do_export_into_sinks() -> Optional[UsageError]:
            try:
                sinks_result = future_sinks.future.result()
                if isinstance(sinks_result, UsageError):
                    return sinks_result
                if state.mode == ExportMode.PREDICTIONS:
                    job_target = ExportTask(operator=classifier, sink=sinks_result[0])
                    job_name = "Pixel Predictions Export"
                else:
                    job_target = ExportAsSimpleSegmentationTask(operator=classifier, sinks=sinks_result)
                    job_name = "Simple Segmentation Export"
                export_job = Job(
                    name=job_name, # FIXME: add datasource url?
                    target=job_target,
                    args=datasource.roi.get_datasource_tiles(),
                    on_progress=on_progress,
                    on_complete=on_complete,
                )
                self.executor.submit_job(export_job)
                with self._lock:
                    self._jobs[export_job.uuid] = export_job
            except Exception as e:
                import traceback
                traceback.print_exc()
                return UsageError(f"Exception while creating data sinks: {e}")
            finally:
                with self._lock:
                    self._sink_creation_tasks.remove(future_sinks)

        future_sinks.future.add_done_callback(lambda _: self._enqueue_interaction(do_export_into_sinks))


Interaction = Callable[[], Optional[UsageError]]

class WsExportApplet(WsApplet, ExportApplet):
    def __init__(
        self,
        *,
        name: str,
        executor: HashingExecutor,
        operator: AppletOutput[Optional[Operator[DataRoi, Array5D]]],
        datasource: AppletOutput[Optional[DataSource]],
        enqueue_interaction: Callable[[Interaction], Any],
        on_job_step_completed: Optional[JobProgressCallback],
        on_job_completed: Optional[JobCompletedCallback],
    ):
        self.lock = threading.Lock()
        self.last_update = time.monotonic()
        self.on_job_completed = on_job_completed
        self.on_job_step_completed = on_job_step_completed
        super().__init__(
            name=name, executor=executor, operator=operator, datasource=datasource, enqueue_interaction=enqueue_interaction
        )

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        if method_name == "set_sink_params":
            bucket_name = Absent.tryGetFromObject(key="sink_bucket_name", json_object=arguments, parser=ensureJsonString)
            sink_prefix = Absent.tryGetFromObject(key="sink_prefix", json_object=arguments, parser=ensureJsonString)
            sink_voxel_offset = Absent.tryGetFromObject(key="sink_voxel_offset", json_object=arguments, parser=ensureJsonIntTripplet)
            sink_encoder = Absent.tryGetFromObject(key="sink_encoder", json_object=arguments, parser=PrecomputedChunksEncoder.from_json_value)
            mode = Absent.tryGetFromObject(key="mode", json_object=arguments, parser=ExportMode.from_json_value)
            rpc_result = self.set_sink_params(
                user_prompt=user_prompt,
                sink_bucket_name=bucket_name,
                sink_prefix=PurePosixPath(sink_prefix) if isinstance(sink_prefix, str) else sink_prefix,
                sink_voxel_offset=sink_voxel_offset or Absent(),
                sink_encoder=sink_encoder or Absent(),
                mode=mode or Absent(),
            )
            if isinstance(rpc_result, PropagationError):
                return UsageError(rpc_result.message)
            return None

        if method_name == "start_export_job":
            job_result = self.start_export_job(
                on_progress=self.on_job_step_completed,
                on_complete=self.on_job_completed,
            )
            if isinstance(job_result, UsageError):
                return job_result
            return None

        if method_name == "cancel_job":
            job_id = uuid.UUID(ensureJsonString(arguments.get("job_id")))
            self.executor.cancel_group(job_id)
            _ = self._jobs.pop(job_id, None)
            return None
        raise ValueError(f"Invalid method name: '{method_name}'")

    def _get_json_state(self) -> JsonObject:
        return {
            "jobs": tuple(job.to_json_value() for job in self._jobs.values()),
            "sink_creation_tasks": tuple(task.to_json_value() for task in self._sink_creation_tasks),
            **self._state.to_json_value()
        }