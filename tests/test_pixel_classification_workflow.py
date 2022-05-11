from pathlib import PurePosixPath
import time
from concurrent.futures import ThreadPoolExecutor
import json

import numpy as np
from ndstructs.utils.json_serializable import JsonObject, ensureJsonArray, ensureJsonInt, ensureJsonObject

from tests import create_precomputed_chunks_sink, get_sample_c_cells_datasource, get_sample_c_cells_pixel_annotations, get_sample_feature_extractors, get_test_output_osfs
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.filesystem.osfs import OsFs
from webilastik.libebrains.user_token import UserToken
from webilastik.scheduling.job import PriorityExecutor
from webilastik.ui.applet import dummy_prompt
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow


def wait_until_jobs_completed(workflow: PixelClassificationWorkflow, timeout: float = 10):
    wait_time = 0.2
    while timeout > 0:
        export_status: JsonObject = workflow.export_applet._get_json_state()
        jobs = ensureJsonArray(export_status["jobs"])
        for job in jobs:
            job_obj = ensureJsonObject(job)
            num_args = ensureJsonInt(job_obj["num_args"])
            num_completed_steps = ensureJsonInt(job_obj["num_completed_steps"])
            if num_completed_steps < num_args:
                print(f"Jobs not done yet. Waiting...")
                time.sleep(wait_time)
                timeout -= wait_time
                break
        else:
            return


def test_pixel_classification_workflow():
    executor = ThreadPoolExecutor()
    priority_executor = PriorityExecutor(executor=executor, num_concurrent_tasks=3)

    workflow = PixelClassificationWorkflow(
        ebrains_user_token=UserToken.get_global_token_or_raise(),
        on_async_change=lambda : print(json.dumps(workflow.export_applet._get_json_state(), indent=4)),
        executor=executor,
        priority_executor=priority_executor,
    )

    # GUI turns on live update
    _ = workflow.pixel_classifier_applet.set_live_update(dummy_prompt, live_update=True)

    # GUI creates some feature extractors
    _ = workflow.feature_selection_applet.add_feature_extractors(
        user_prompt=dummy_prompt,
        feature_extractors=get_sample_feature_extractors(),
    )

    pixel_annotations = get_sample_c_cells_pixel_annotations()

    # GUI creates some annotations
    _ = workflow.brushing_applet.add_annotations(
        user_prompt=dummy_prompt,
        annotations=pixel_annotations,
    )

    while workflow.pixel_classifier_applet.pixel_classifier() is None:
        time.sleep(0.2)

    classifier = workflow.pixel_classifier_applet.pixel_classifier()
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
    result = workflow.export_applet.start_export_job(
        datasource=raw_data_source,
        datasink=predictions_export_datasink
    )
    assert result is None

    print(f"---> Job successfully scheduled? Waiting for a while")
    wait_until_jobs_completed(workflow=workflow)
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
    result = workflow.export_applet.start_simple_segmentation_export_job(
        datasource=raw_data_source,
        datasinks=simple_segmentation_datasinks,
    )

    print(f"---> Job successfully scheduled? Waiting for a while")
    wait_until_jobs_completed(workflow=workflow)
    print(f"Done waiting. Checking outputs")

    segmentation_output_1 = PrecomputedChunksDataSource(
        filesystem=output_fs,
        path=simple_segmentation_datasinks[1].path,
        resolution=(1,1,1)
    )
    for tile in segmentation_output_1.roi.get_datasource_tiles():
        tile.retrieve().show_images()

###################################

    _ = workflow.save_project(fs=OsFs("/tmp"), path=PurePosixPath("test_pixel_classification_workflow.ilp"))
    # compare_projects(Path("/tmp/my_test.ilp"), Path("/home/builder/TrainedPixelClassMaster.ilp"))

####################################3

    priority_executor.shutdown()

##################################################3333
if __name__ == "__main__":
    test_pixel_classification_workflow()
