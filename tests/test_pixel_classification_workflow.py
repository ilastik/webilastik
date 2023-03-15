from pathlib import Path, PurePosixPath
import time
from concurrent.futures import ProcessPoolExecutor
import json
from typing import List

import numpy as np
from ndstructs.utils.json_serializable import JsonObject, ensureJsonArray, ensureJsonInt, ensureJsonObject

from tests import create_precomputed_chunks_sink, get_sample_c_cells_datasource, get_sample_c_cells_pixel_annotations, get_test_output_path
from webilastik.datasource import DataRoi
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.features.ilp_filter import (
    IlpDifferenceOfGaussians, IlpGaussianGradientMagnitude, IlpGaussianSmoothing,
    IlpHessianOfGaussianEigenvalues, IlpLaplacianOfGaussian, IlpStructureTensorEigenvalues,
)
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem.os_fs import OsFs
from webilastik.libebrains.user_token import UserToken
from webilastik.scheduling.job import PriorityExecutor
from webilastik.ui.applet import dummy_prompt
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow
from webilastik.utility.url import Protocol, Url
from executor_getter import get_executor

test_output_path = get_test_output_path()

def wait_until_jobs_completed(workflow: PixelClassificationWorkflow, timeout: float = 50):
    wait_time = 0.5
    while timeout > 0:
        export_state = workflow.export_applet.get_state_dto()
        for job in export_state.jobs:
            num_args = job.num_args
            num_completed_steps = job.num_completed_steps
            print("checkign,....")
            print(f"job {num_args=}  {num_completed_steps=}")
            if num_completed_steps < (num_args or float("inf")):
                print(f"Jobs not done yet. Waiting...")
                time.sleep(wait_time)
                timeout -= wait_time
                break
        else:
            return
    raise TimeoutError("Waiting on jobs timed out!")


def test_pixel_classification_workflow():
    executor = get_executor(hint="server_tile_handler")
    priority_executor = PriorityExecutor(executor=executor, max_active_job_steps=8)

    workflow = PixelClassificationWorkflow(
        on_async_change=lambda : print(json.dumps(workflow.export_applet._get_json_state(), indent=4)),
        executor=executor,
        priority_executor=priority_executor,
    )

    # GUI turns on live update
    _ = workflow.pixel_classifier_applet.set_live_update(dummy_prompt, live_update=True)

    # GUI creates some feature extractors

    all_feature_extractors: List[IlpFilter] = []
    for scale in [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0][0:3]:
        all_feature_extractors.append(IlpGaussianSmoothing(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.append(IlpLaplacianOfGaussian(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.append(IlpGaussianGradientMagnitude(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.append(IlpDifferenceOfGaussians(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.append(IlpStructureTensorEigenvalues(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.append(IlpHessianOfGaussianEigenvalues(ilp_scale=scale, axis_2d="z"))



    _ = workflow.feature_selection_applet.add_feature_extractors(
        user_prompt=dummy_prompt,
        feature_extractors=all_feature_extractors,
    )

    pixel_annotations = get_sample_c_cells_pixel_annotations()
    for label_name, label in zip(workflow.brushing_applet.label_names(), pixel_annotations):
        for a in label.annotations:
            result = workflow.brushing_applet.add_annotation(
                user_prompt=dummy_prompt,
                label_name=label_name,
                annotation=a,
            )
            assert result.is_ok()

    while workflow.pixel_classifier_applet.pixel_classifier() is None:
        time.sleep(0.2)

    classifier = workflow.pixel_classifier_applet.pixel_classifier()
    assert classifier != None




    fs = OsFs.create()
    assert not isinstance(fs, Exception)
    _ = workflow.save_project(fs=fs, path=test_output_path / "blas.ilp")

    loaded_workflow = PixelClassificationWorkflow.from_ilp(
        original_ilp_fs=fs,
        temp_ilp_path=Path(test_output_path / "blas.ilp"),
        on_async_change=lambda : print(json.dumps(workflow.export_applet._get_json_state(), indent=4)),
        executor=executor,
        priority_executor=priority_executor,
    )
    print(loaded_workflow)
    assert isinstance(loaded_workflow, PixelClassificationWorkflow)
    print(f"Loaded workflow and state pixel aplet description is {loaded_workflow.pixel_classifier_applet._state.description}")





    # # calculate predictions on an entire data source
    raw_data_source = get_sample_c_cells_datasource()
    preds_future = executor.submit(classifier, raw_data_source.roi)
    _local_predictions = preds_future.result()
    # _local_predictions.as_uint8().show_channels()

    # # calculate predictions on just a piece of arbitrary data
    _exported_tile = executor.submit(classifier, DataRoi(datasource=raw_data_source, x=(100, 200), y=(100, 200)))
    # _exported_tile.result().show_channels()

###################################


#######################################33

    # run an export job
    predictions_export_datasink = create_precomputed_chunks_sink(
        shape=raw_data_source.shape.updated(c=classifier.num_classes),
        dtype=np.dtype("float32"),
        chunk_size=raw_data_source.tile_shape.updated(c=classifier.num_classes),
    )

    print(f"Sending predictions job request??????")
    result = workflow.export_applet.launch_pixel_probabilities_export_job(
        datasource=raw_data_source,
        datasink=predictions_export_datasink
    )
    assert result is None

    print(f"---> Job successfully scheduled? Waiting for a while")
    wait_until_jobs_completed(workflow=workflow)
    print(f"Done waiting. Checking outputs")

    predictions_output = predictions_export_datasink.to_datasource()
    for tile in predictions_output.roi.get_datasource_tiles():
        _ = tile.retrieve().cut(c=1).as_uint8(normalized=True)#.show_channels()

##################################333

    simple_segmentation_datasink = create_precomputed_chunks_sink(
        shape=raw_data_source.shape.updated(c=3),
        dtype=np.dtype("uint8"),
        chunk_size=raw_data_source.tile_shape.updated(c=3),
    )

    print(f"Sending simple segmentation job request??????")
    result = workflow.export_applet.launch_simple_segmentation_export_job(
        datasource=raw_data_source,
        datasink=simple_segmentation_datasink,
        label_name=pixel_annotations[1].name,
    )

    print(f"---> Job successfully scheduled? Waiting for a while")
    wait_until_jobs_completed(workflow=workflow)
    print(f"Done waiting. Checking outputs")

    segmentation_output_1 = simple_segmentation_datasink.to_datasource()
    for tile in segmentation_output_1.roi.get_datasource_tiles():
        _ = tile.retrieve()#.show_images()

####################################3

    priority_executor.shutdown()

##################################################3333
if __name__ == "__main__":
    test_pixel_classification_workflow()
