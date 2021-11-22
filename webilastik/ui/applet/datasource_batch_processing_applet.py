# pyright: strict

from typing import Optional

from ndstructs.array5D import Array5D

from webilastik.operator import Operator
from webilastik.scheduling.hashing_executor import HashingExecutor, Job, JobCompletedCallback, JobProgressCallback
from webilastik.ui.applet import InertApplet, NoSnapshotApplet, UserPrompt, AppletOutput
from webilastik.datasource import DataRoi, DataSource
from webilastik.datasink import DataSink
from webilastik.ui.applet import UserPrompt

class DatasourceBatchProcessingApplet(NoSnapshotApplet, InertApplet):
    def __init__(self, *, name: str, executor: HashingExecutor, operator: AppletOutput[Optional[Operator[DataRoi, Array5D]]]):
        self._in_operator = operator
        self.executor = executor
        super().__init__(name=name)

    def start_export_job(
        self,
        *,
        user_prompt: UserPrompt,
        source: DataSource,
        sink: DataSink,
        on_progress: Optional[JobProgressCallback] = None,
        on_complete: Optional[JobCompletedCallback] = None,
    ) -> Job[DataRoi]:
        operator = self._in_operator()
        if operator is None:
            raise Exception("Classifier not ready yet") #FIXME
        return self.executor.submit_job(
            target=_ComputeAndSave(operator=operator, sink=sink),
            args=source.roi.get_datasource_tiles(),
            on_progress=on_progress,
            on_complete=on_complete,
        )


class _ComputeAndSave:
    def __init__(self, operator: Operator[DataRoi, Array5D], sink: DataSink):
        self.operator = operator
        self.sink = sink

    def __call__(self, step: DataRoi) -> None:
        tile = self.operator.compute(step)
        self.sink.write(tile)