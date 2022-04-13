import time
from concurrent.futures import ThreadPoolExecutor
import json

import numpy as np

from tests import create_precomputed_chunks_sink, get_sample_c_cells_datasource, get_sample_c_cells_pixel_annotations, get_sample_feature_extractors, get_test_output_osfs
from webilastik.datasource import DataRoi, FsDataSource
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.scheduling.job import PriorityExecutor
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.brushing_applet import BrushingApplet
from webilastik.ui.applet import dummy_prompt
from webilastik.ui.applet.pixel_predictions_export_applet import WsPixelClassificationExportApplet
from webilastik.ui.applet.ws_pixel_classification_applet import WsPixelClassificationApplet




if __name__ == "__main__":
    executor = ThreadPoolExecutor(max_workers=4)
    priority_executor = PriorityExecutor(executor=executor, num_concurrent_tasks=2)


    brushing_applet = BrushingApplet("brushing_applet")
    feature_selection_applet = FeatureSelectionApplet("feature_selection_applet", datasources=brushing_applet.datasources)
    pixel_classifier_applet = WsPixelClassificationApplet(
        name="pixel_classifier_applet",
        feature_extractors=feature_selection_applet.feature_extractors,
        annotations=brushing_applet.annotations,
        executor=executor,
        on_async_change=lambda : None,#print(f"Pixel classifier applet changed! {json.dumps(pixel_classifier_applet._get_json_state(), indent=4)}")
    )
    export_applet = WsPixelClassificationExportApplet(
        name="pixel_classification_export_applet",
        on_async_change=lambda : print(json.dumps(export_applet._get_json_state(), indent=4)),
        priority_executor=priority_executor,
        operator=pixel_classifier_applet.pixel_classifier,
        datasource_suggestions=brushing_applet.datasources.transformed_with(
            lambda datasources: tuple(ds for ds in datasources if isinstance(ds, FsDataSource))
        )
    )

    # GUI turns on live update
    _ = pixel_classifier_applet.set_live_update(dummy_prompt, live_update=True)

    # GUI creates some feature extractors
    _ = feature_selection_applet.add_feature_extractors(
        user_prompt=dummy_prompt,
        feature_extractors=get_sample_feature_extractors(),
    )

    pixel_annotations = get_sample_c_cells_pixel_annotations()

    # GUI creates some annotations
    _ = brushing_applet.add_annotations(
        user_prompt=dummy_prompt,
        annotations=pixel_annotations,
    )

    time.sleep(3)

    classifier = pixel_classifier_applet.pixel_classifier()
    assert classifier != None

    # # calculate predictions on an entire data source
    raw_data_source = get_sample_c_cells_datasource()
    # preds_future = executor.submit(classifier.compute, raw_data_source.roi)
    # local_predictions = preds_future.result()
    # local_predictions.as_uint8().show_channels()

    # # calculate predictions on just a piece of arbitrary data
    # exported_tile = executor.submit(classifier.compute, DataRoi(datasource=raw_data_source, x=(100, 200), y=(100, 200)))
    # exported_tile.result().show_channels()

    # run an export job
    output_fs = get_test_output_osfs()
    predictions_export_datasink = create_precomputed_chunks_sink(
        shape=raw_data_source.shape.updated(c=classifier.num_classes),
        dtype=np.dtype("float32"),
        chunk_size=raw_data_source.tile_shape.updated(c=classifier.num_classes),
        fs=output_fs
    )

    print(f"Sending predictions job request??????")
    result = export_applet.start_export_job(
        datasource=raw_data_source,
        datasink=predictions_export_datasink
    )
    assert result is None

    print(f"---> Job successfully scheduled? Waiting for a while")
    time.sleep(10)
    print(f"Done waiting. Checking outputs")


    predictions_output = PrecomputedChunksDataSource(
        filesystem=output_fs,
        path=predictions_export_datasink.path,
        resolution=(1,1,1)
    )
    for tile in predictions_output.roi.get_datasource_tiles():
        tile.retrieve().cut(c=1).as_uint8(normalized=True).show_channels()

##################################333

    simple_segmentation_datasinks = [
        create_precomputed_chunks_sink(
            shape=raw_data_source.shape.updated(c=3),
            dtype=np.dtype("uint8"),
            chunk_size=raw_data_source.tile_shape.updated(c=3),
            fs=output_fs
        ),
        create_precomputed_chunks_sink(
            shape=raw_data_source.shape.updated(c=3),
            dtype=np.dtype("uint8"),
            chunk_size=raw_data_source.tile_shape.updated(c=3),
            fs=output_fs
        ),
    ]

    print(f"Sending simple segmentation job request??????")
    result = export_applet.start_simple_segmentation_export_job(
        datasource=raw_data_source,
        datasinks=simple_segmentation_datasinks,
    )

    print(f"---> Job successfully scheduled? Waiting for a while")
    time.sleep(5)
    print(f"Done waiting. Checking outputs")

    segmentation_output_1 = PrecomputedChunksDataSource(
        filesystem=output_fs,
        path=simple_segmentation_datasinks[1].path,
        resolution=(1,1,1)
    )
    for tile in segmentation_output_1.roi.get_datasource_tiles():
        tile.retrieve().show_images()


##################################################3333

    priority_executor.shutdown()
    executor.shutdown()
