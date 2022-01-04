# pyright: strict

from typing import Optional, Sequence, Union

import numpy as np

from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.features.ilp_filter import IlpFilter
from webilastik.libebrains.user_token import UserToken
from webilastik.scheduling.hashing_executor import HashingExecutor, Job, JobCompletedCallback, JobProgressCallback
from webilastik.ui.applet import AppletOutput, InertApplet, NoSnapshotApplet
from webilastik.datasource import DataRoi, DataSource
from webilastik.datasink import DataSink
from webilastik.ui.datasink import DataSinkCreationParams
from webilastik.ui.datasource import try_load_datasource_from_url
from webilastik.ui.usage_error import UsageError
from webilastik.utility.url import Protocol, Url

class PixelClassificationExportJob(Job[DataRoi]):
    def __init__(
        self,
        *,
        classifier: VigraPixelClassifier[IlpFilter],
        source: DataSource,
        sink: DataSink,
        on_progress: Optional[JobProgressCallback] = None,
        on_complete: Optional[JobCompletedCallback] = None
    ):
        def target(step: DataRoi):
            tile = classifier.compute(step)
            sink.write(tile)

        super().__init__(
            name="Pixel Classification Export",
            target=target,
            args=source.roi.get_datasource_tiles(),
            on_progress=on_progress,
            on_complete=on_complete
        )

ClassifierOutput = AppletOutput[Optional[VigraPixelClassifier[IlpFilter]]]

class PixelClasificationExportingApplet(NoSnapshotApplet, InertApplet):
    def __init__(self, *, name: str, executor: HashingExecutor, classifier: ClassifierOutput):
        self._in_classifier = classifier
        self.executor = executor
        super().__init__(name=name)

    def start_export_job(
        self,
        *,
        source_url: Url,
        sink_params: DataSinkCreationParams,
        ebrains_user_token: Optional[UserToken] = None,
        allowed_protocols: Sequence[Protocol] = (Protocol.HTTP, Protocol.HTTPS),
        on_progress: Optional[JobProgressCallback] = None,
        on_complete: Optional[JobCompletedCallback] = None,
    ) -> Union[PixelClassificationExportJob, UsageError]:
        classifier = self._in_classifier()
        if classifier is None:
            return UsageError("Classifier not ready yet")

        source = try_load_datasource_from_url(
            url=source_url,
            ebrains_user_token=ebrains_user_token,
            allowed_protocols=allowed_protocols,
        )
        if isinstance(source, UsageError):
            return source

        sink = sink_params.try_load(
            ebrains_user_token=ebrains_user_token,
            dtype=np.dtype("float32"),
            location=source.location,
            interval=source.interval.updated(c=(0, classifier.num_classes)),
            chunk_size=source.tile_shape,
            spatial_resolution=source.spatial_resolution,
        )
        if isinstance(sink, UsageError):
            return sink

        job = PixelClassificationExportJob(
            classifier=classifier,
            source=source,
            sink=sink,
            on_progress=on_progress,
            on_complete=on_complete,
        )
        self.executor.submit_job(job)
        return job