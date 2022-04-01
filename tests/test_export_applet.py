from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import PurePosixPath
import time

import numpy as np

from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasource import DataSource
from webilastik.datasource.skimage_datasource import SkimageDataSource
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem.osfs import OsFs
from webilastik.scheduling.job import JobExecutor
from webilastik.ui.applet import Applet, StatelesApplet, applet_output
from webilastik.ui.applet.pixel_predictions_export_applet import PixelClassificationExportApplet

from tests import create_precomputed_chunks_sink, get_sample_c_cells_datasource, get_sample_c_cells_pixel_classifier

class DummyPixelClassificationApplet(StatelesApplet):
    def __init__(self, name: str) -> None:
        super().__init__(name)

    @applet_output
    def classifier(self) -> VigraPixelClassifier[IlpFilter]:
        return get_sample_c_cells_pixel_classifier()

if __name__ == "__main__":
    executor = ThreadPoolExecutor(max_workers=4)
    job_executor= JobExecutor(executor=executor, concurrent_job_steps=2)

    pixel_classifier_applet = DummyPixelClassificationApplet("reader_applet")
    export_applet = PixelClassificationExportApplet(
        name="export_applet",
        on_async_change=lambda: print(f"something_changed"),
        executor=executor,
        job_executor=job_executor,
        operator=pixel_classifier_applet.classifier,
    )

    datasource = get_sample_c_cells_datasource()

    result = export_applet.create_export_job(
        datasource=get_sample_c_cells_datasource(),
        datasink=create_precomputed_chunks_sink(
            shape=datasource.shape.updated(c=2),
            dtype=np.dtype("float32"),
            chunk_size=datasource.tile_shape,
        )
    )
    if isinstance(result, Exception):
        raise result

    time.sleep(8)

    print(f"trying to shutdown JOB executor?")
    job_executor.shutdown()
    print(f"DONE shutting down JOB executor")

    print(f"trying to shutdown executor?")
    executor.shutdown()

    print(f"managed to shutdown executor, i think")


