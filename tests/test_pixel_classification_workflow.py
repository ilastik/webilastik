from pathlib import Path
import time
import json
from typing import List

import numpy as np

from tests import TEST_OUTPUT_PATH, create_precomputed_chunks_sink, get_sample_c_cells_datasource, get_sample_c_cells_pixel_annotations
from webilastik.datasource import DataRoi
from webilastik.features.ilp_filter import (
    IlpDifferenceOfGaussians, IlpGaussianGradientMagnitude, IlpGaussianSmoothing,
    IlpHessianOfGaussianEigenvalues, IlpLaplacianOfGaussian, IlpStructureTensorEigenvalues,
)
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem.os_fs import OsFs
from webilastik.scheduling.job import PriorityExecutor
from webilastik.ui.applet import dummy_prompt
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow
from webilastik.utility import eprint
from executor_getter import get_executor

def wait_until_jobs_completed(workflow: PixelClassificationWorkflow, timeout: float = 50):
    wait_time = 0.5
    while timeout > 0:
        export_state = workflow.export_applet.get_state_dto()
        for job in export_state.jobs:
            num_args = job.num_args
            num_completed_steps = job.num_completed_steps
            eprint(f"job {num_args=}  {num_completed_steps=}", level="debug")
            if num_completed_steps < (num_args or float("inf")):
                eprint(f"Jobs not done yet. Waiting...", level="debug")
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
        # on_async_change=lambda : eprint(json.dumps(workflow.export_applet._get_json_state(), indent=4), level="debug"),
        on_async_change=lambda : None,
        executor=executor,
        priority_executor=priority_executor,
        ebrains_user_credentials=None,
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
    project_path = TEST_OUTPUT_PATH / "my_project.ilp"
    _ = workflow.save_project(fs=fs, path=project_path)

    loaded_workflow = PixelClassificationWorkflow.from_ilp(
        ilp_path=Path(project_path),
        # on_async_change=lambda : eprint(json.dumps(workflow.export_applet._get_json_state(), indent=4), level="debug"),
        on_async_change=lambda: None,
        executor=executor,
        priority_executor=priority_executor,
        ebrains_user_credentials=None,
    )
    assert isinstance(loaded_workflow, PixelClassificationWorkflow)


    # # calculate predictions on an entire data source
    raw_data_source = get_sample_c_cells_datasource()
    preds_future = executor.submit(classifier, raw_data_source.roi)
    local_predictions = preds_future.result()
    # local_predictions.as_uint8().show_channels()

    # # calculate predictions on just a piece of arbitrary data
    exported_tile = executor.submit(classifier, DataRoi(datasource=raw_data_source, x=(100, 200), y=(100, 200)))
    # exported_tile.result().show_channels()

###################################


#######################################33

    output_fs = OsFs.create()
    assert not isinstance(output_fs, Exception)
    # run an export job
    predictions_export_datasink = create_precomputed_chunks_sink(
        shape=raw_data_source.shape.updated(c=classifier.num_classes),
        dtype=np.dtype("float32"),
        chunk_size=raw_data_source.tile_shape.updated(c=classifier.num_classes),
        fs=output_fs,
        name="pixel_classification_workflow__predictions__export.precomputed",
    )

    eprint(f"Sending predictions job request??????", level="debug")
    result = workflow.export_applet.launch_pixel_probabilities_export_job(
        datasource=raw_data_source,
        datasink=predictions_export_datasink
    )
    assert result is None

    eprint(f"---> Job successfully scheduled? Waiting for a while", level="debug")
    wait_until_jobs_completed(workflow=workflow)
    eprint(f"Done waiting. Checking outputs", level="debug")

    predictions_output = predictions_export_datasink.to_datasource()
    for tile in predictions_output.roi.get_datasource_tiles():
        _ = tile.retrieve().cut(c=1).as_uint8(normalized=True)#.show_channels()

##################################333

    simple_segmentation_datasink = create_precomputed_chunks_sink(
        shape=raw_data_source.shape.updated(c=3),
        dtype=np.dtype("uint8"),
        chunk_size=raw_data_source.tile_shape.updated(c=3),
        fs=output_fs,
        name="pixel_classification_workflow__segmentation__export.precomputed",
    )

    eprint(f"Sending simple segmentation job request??????", level="debug")
    result = workflow.export_applet.launch_simple_segmentation_export_job(
        datasource=raw_data_source,
        datasink=simple_segmentation_datasink,
        label_name=pixel_annotations[1].name,
    )

    eprint(f"---> Job successfully scheduled? Waiting for a while", level="debug")
    wait_until_jobs_completed(workflow=workflow)
    eprint(f"Done waiting. Checking outputs", level="debug")

    segmentation_output_1 = simple_segmentation_datasink.to_datasource()
    for tile in segmentation_output_1.roi.get_datasource_tiles():
        _ = tile.retrieve()#.show_images()

####################################3

    priority_executor.shutdown()

##################################################3333
if __name__ == "__main__":
    test_pixel_classification_workflow()
