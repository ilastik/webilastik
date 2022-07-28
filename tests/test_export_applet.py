from concurrent.futures.thread import ThreadPoolExecutor
import time
from typing import Sequence

import numpy as np

from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasource import FsDataSource
from webilastik.features.ilp_filter import IlpFilter
from webilastik.scheduling.job import PriorityExecutor
from webilastik.ui.applet import StatelesApplet, applet_output
from webilastik.ui.applet.pixel_predictions_export_applet import PixelClassificationExportApplet

from tests import create_precomputed_chunks_sink, get_sample_c_cells_datasource, get_sample_c_cells_pixel_classifier

class DummyPixelClassificationApplet(StatelesApplet):
    def __init__(self, name: str) -> None:
        super().__init__(name)

    @applet_output
    def classifier(self) -> VigraPixelClassifier[IlpFilter]:
        return get_sample_c_cells_pixel_classifier()

class DummyDatasourceApplet(StatelesApplet):
    @applet_output
    def datasources(self) -> "Sequence[FsDataSource] | None":
        return None


if __name__ == "__main__":
    executor = ThreadPoolExecutor(max_workers=4)
    priority_executor= PriorityExecutor(executor=executor, max_active_job_steps=2)



    pixel_classifier_applet = DummyPixelClassificationApplet("reader_applet")
    export_applet = PixelClassificationExportApplet(
        name="export_applet",
        on_async_change=lambda: print(f"something_changed"),
        priority_executor=priority_executor,
        operator=pixel_classifier_applet.classifier,
        datasource_suggestions=DummyDatasourceApplet(name="datasource propvider applet").datasources,
    )

    datasource = get_sample_c_cells_datasource()

    result = export_applet.start_export_job(
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
    priority_executor.shutdown()
    print(f"DONE shutting down JOB executor")

    print(f"trying to shutdown executor?")
    executor.shutdown()

    print(f"managed to shutdown executor, i think")


