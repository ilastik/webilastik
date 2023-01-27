from concurrent.futures.thread import ThreadPoolExecutor
import time
from typing import Sequence

import numpy as np

from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasource import FsDataSource
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem.os_fs import OsFs
from webilastik.scheduling.job import PriorityExecutor
from webilastik.ui.applet import StatelesApplet, applet_output
from webilastik.ui.applet.brushing_applet import Label
from webilastik.ui.applet.pixel_predictions_export_applet import PixelClassificationExportApplet

from tests import SkipException, create_precomputed_chunks_sink, get_sample_c_cells_datasource, get_sample_c_cells_pixel_annotations, get_sample_c_cells_pixel_classifier, run_all_tests
from webilastik.utility import eprint

class DummyBrushingApplet(StatelesApplet):
    def __init__(self, name: str) -> None:
        super().__init__(name)

    @applet_output
    def labels(self) -> Sequence[Label]:
        return get_sample_c_cells_pixel_annotations()

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

def test_export_applet():
    executor = ThreadPoolExecutor(max_workers=4)
    priority_executor= PriorityExecutor(executor=executor, max_active_job_steps=2)

    pixel_classifier_applet = DummyPixelClassificationApplet("reader_applet")
    export_applet = PixelClassificationExportApplet(
        name="export_applet",
        on_async_change=lambda: eprint(f"something changed in export applet", level="debug"),
        priority_executor=priority_executor,
        operator=pixel_classifier_applet.classifier,
        populated_labels=DummyBrushingApplet("brushing_applet").labels,
        datasource_suggestions=DummyDatasourceApplet(name="datasource propvider applet").datasources,
        ebrains_user_credentials=None,
    )

    output_fs = OsFs.create()
    assert not isinstance(output_fs, Exception)
    datasource = get_sample_c_cells_datasource()
    datasink_result = create_precomputed_chunks_sink(
        shape=datasource.shape.updated(c=2),
        dtype=np.dtype("float32"),
        chunk_size=datasource.tile_shape,
        fs=output_fs,
        name="export_applet_output.precomputed"
    )

    result = export_applet.launch_pixel_probabilities_export_job(
        datasource=get_sample_c_cells_datasource(),
        datasink=datasink_result,
    )
    if isinstance(result, Exception):
        raise result

    time.sleep(2)

    eprint(f"trying to shutdown JOB executor?", level="debug")
    priority_executor.shutdown()
    eprint(f"DONE shutting down JOB executor", level="debug")

    eprint(f"trying to shutdown executor?", level="debug")
    executor.shutdown()

    eprint(f"managed to shutdown executor, i think", level="debug")


if __name__ == "__main__":
    import sys
    run_all_tests(sys.modules[__name__])