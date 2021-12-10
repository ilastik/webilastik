# pyright: strict

from typing import Optional

from ndstructs.array5D import Array5D
from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.features.ilp_filter import IlpFilter

from webilastik.operator import Operator
from webilastik.scheduling.hashing_executor import HashingExecutor, Job, JobCompletedCallback, JobProgressCallback
from webilastik.ui.applet import AppletOutput, InertApplet, NoSnapshotApplet, UserPrompt
from webilastik.datasource import DataRoi, DataSource
from webilastik.datasink import DataSink

class _ComputeAndSave:
    def __init__(self, operator: Operator[DataRoi, Array5D], sink: DataSink):
        self.operator = operator
        self.sink = sink

    def __call__(self, step: DataRoi) -> None:
        tile = self.operator.compute(step)
        self.sink.write(tile)

ClassifierOutput = AppletOutput[Optional[VigraPixelClassifier[IlpFilter]]]

class PixelClasificationExportingApplet(NoSnapshotApplet, InertApplet):
    def __init__(self, *, name: str, executor: HashingExecutor, classifier: ClassifierOutput):
        self._in_classifier = classifier
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
        classifier = self._in_classifier()
        if classifier is None:
            raise Exception("Classifier not ready yet") #FIXME

        return self.executor.submit_job(
            name=f"Pixel Classification Export",
            target=_ComputeAndSave(operator=classifier, sink=sink),
            args=source.roi.get_datasource_tiles(),
            on_progress=on_progress,
            on_complete=on_complete,
        )