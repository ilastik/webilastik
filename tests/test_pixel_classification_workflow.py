import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from tests import create_precomputed_chunks_sink, get_sample_c_cells_datasource, get_sample_c_cells_pixel_annotations, get_sample_feature_extractors
from webilastik.datasource import DataRoi
from webilastik.scheduling.job import JobExecutor
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.brushing_applet import BrushingApplet
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet
from webilastik.ui.applet import dummy_prompt
from webilastik.ui.applet.pixel_predictions_export_applet import PixelClassificationExportApplet



if __name__ == "__main__":
    executor = ThreadPoolExecutor(max_workers=4)
    job_executor = JobExecutor(executor=executor, concurrent_job_steps=2)


    brushing_applet = BrushingApplet("brushing_applet")
    feature_selection_applet = FeatureSelectionApplet("feature_selection_applet", datasources=brushing_applet.datasources)
    pixel_classifier_applet = PixelClassificationApplet(
        name="pixel_classifier_applet",
        feature_extractors=feature_selection_applet.feature_extractors,
        annotations=brushing_applet.annotations,
        executor=executor,
        on_async_change=lambda : print(f"Pixel classifier training is prolly done")
    )
    export_applet = PixelClassificationExportApplet(
        name="pixel_classification_export_applet",
        on_async_change=lambda : print(f"Export changed something..."),
        executor=executor,
        job_executor=job_executor,
        operator=pixel_classifier_applet.pixel_classifier,
    )

    # GUI turns on live update
    _ = pixel_classifier_applet.set_live_update(dummy_prompt, live_update=True)

    # GUI creates some feature extractors
    _ = feature_selection_applet.add_feature_extractors(
        user_prompt=dummy_prompt,
        feature_extractors=get_sample_feature_extractors(),
    )
    assert len(feature_selection_applet.feature_extractors()) == 2

    pixel_annotations = get_sample_c_cells_pixel_annotations()

    # GUI creates some annotations
    _ = brushing_applet.add_annotations(
        user_prompt=dummy_prompt,
        annotations=pixel_annotations,
    )

    time.sleep(3)

    classifier = pixel_classifier_applet.pixel_classifier()
    assert classifier != None

    # calculate predictions on an entire data source
    raw_data_source = get_sample_c_cells_datasource()
    preds_future = executor.submit(classifier.compute, raw_data_source.roi)
    local_predictions = preds_future.result()
    local_predictions.as_uint8().show_channels()

    # calculate predictions on just a piece of arbitrary data
    exported_tile = executor.submit(classifier.compute, DataRoi(datasource=raw_data_source, x=(100, 200), y=(100, 200)))
    exported_tile.result().show_channels()

    # try running an export job
    sink = create_precomputed_chunks_sink(
        shape=raw_data_source.shape.updated(c=classifier.num_classes),
        dtype=np.dtype("float32"),
        chunk_size=raw_data_source.tile_shape
    )
    export_result = export_applet.start_export_job(
        datasource=raw_data_source,
        datasink=sink,
    )
    assert export_result is None
    time.sleep(7)

    # while job.status in ("pending", "running"):
    #     time.sleep(1)
    # assert job.status == "succeeded"

    # retrieved_predictions = sink.to_datasource().retrieve()
    # assert local_predictions == retrieved_predictions
    # retrieved_predictions.as_uint8().show_channels()

    #try removing a brush stroke
    _ = brushing_applet.remove_annotations(dummy_prompt, pixel_annotations[0:1])
    assert tuple(brushing_applet.annotations()) == tuple(pixel_annotations[1:])

    # for png_bytes in preds.to_z_slice_pngs():
    #     path = f"/tmp/junk_test_image_{uuid.uuid4()}.png"
    #     with open(path, "wb") as outfile:
    #         outfile.write(png_bytes.getbuffer())
    #     os.system(f"gimp {path}")

    job_executor.shutdown()
    executor.shutdown()
