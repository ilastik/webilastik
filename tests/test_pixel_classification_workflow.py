from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor
import json
from typing import Set
import h5py
import shutil

import numpy as np
from ndstructs.point5D import Point5D
from ndstructs.utils.json_serializable import JsonObject, ensureJsonArray, ensureJsonInt, ensureJsonObject

from tests import create_precomputed_chunks_sink, get_sample_c_cells_datasource, get_sample_c_cells_pixel_annotations, get_sample_feature_extractors, get_test_output_osfs
from webilastik.annotations.annotation import Color
from webilastik.classic_ilastik.ilp import IlpFeatureSelectionsGroup, ensure_group
from webilastik.classic_ilastik.ilp.pixel_classification_ilp import IlpPixelClassificationGroup, IlpPixelClassificationWorkflowGroup
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.features.channelwise_fastfilters import DifferenceOfGaussians, GaussianGradientMagnitude, GaussianSmoothing, HessianOfGaussianEigenvalues, LaplacianOfGaussian, StructureTensorEigenvalues
from webilastik.filesystem.osfs import OsFs
from webilastik.libebrains.user_token import UserToken
from webilastik.scheduling.job import PriorityExecutor
from webilastik.ui.applet import dummy_prompt
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow
from webilastik.utility.url import Protocol


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


    # # calculate predictions on an entire data source
    raw_data_source = get_sample_c_cells_datasource()
    # preds_future = executor.submit(classifier.compute, raw_data_source.roi)
    # local_predictions = preds_future.result()
    # local_predictions.as_uint8().show_channels()

    # # calculate predictions on just a piece of arbitrary data
    # exported_tile = executor.submit(classifier.compute, DataRoi(datasource=raw_data_source, x=(100, 200), y=(100, 200)))
    # exported_tile.result().show_channels()

###################################

    sample_trained_ilp_path = Path("tests/projects/TrainedPixelClassification.ilp")
    output_ilp_path = Path("/tmp/rewritten.ilp")

    with h5py.File(sample_trained_ilp_path, "r") as f:
        sample_workflow_data = IlpPixelClassificationWorkflowGroup.parse(
            group=f,
            ilp_fs=OsFs("."),
            allowed_protocols=[Protocol.FILE],
        )
        assert not isinstance(sample_workflow_data, Exception)
        with open(output_ilp_path, "wb") as rewritten:
            _ = rewritten.write(sample_workflow_data.to_h5_file_bytes())
        shutil.copy("tests/projects/c_cells_1.png", output_ilp_path.parent.joinpath("c_cells_1.png"))

    with h5py.File(output_ilp_path, "r") as rewritten:
        reloaded_data = IlpPixelClassificationWorkflowGroup.parse(
            group=rewritten,
            ilp_fs=OsFs("/"),
            allowed_protocols=[Protocol.FILE],
        )
        assert not isinstance(reloaded_data, Exception)

        loaded_feature_extractors = reloaded_data.FeatureSelections.feature_extractors
        assert GaussianSmoothing.from_ilp_scale(scale=0.3, axis_2d="z") in loaded_feature_extractors
        assert LaplacianOfGaussian.from_ilp_scale(scale=0.7, axis_2d="z") in loaded_feature_extractors
        assert GaussianGradientMagnitude.from_ilp_scale(scale=1.0, axis_2d="z") in loaded_feature_extractors
        assert DifferenceOfGaussians.from_ilp_scale(scale=1.6, axis_2d="z") in loaded_feature_extractors
        assert StructureTensorEigenvalues.from_ilp_scale(scale=3.5, axis_2d="z") in loaded_feature_extractors
        assert HessianOfGaussianEigenvalues.from_ilp_scale(scale=5.0, axis_2d="z") in loaded_feature_extractors
        assert len(loaded_feature_extractors) == 6

        loaded_labels = reloaded_data.PixelClassification.labels
        for label in loaded_labels:
            loaded_points: Set[Point5D] = set()
            for a in label.annotations:
                loaded_points.update(a.to_points())
            if label.color == Color(r=np.uint8(255), g=np.uint8(225),  b=np.uint8(25)):
                assert loaded_points == set([Point5D(x=200, y=200), Point5D(x=201, y=201), Point5D(x=202, y=202)])
            elif label.color == Color(r=np.uint8(0), g=np.uint8(130),  b=np.uint8(200)):
                assert loaded_points == set([Point5D(x=400, y=400), Point5D(x=401, y=401), Point5D(x=402, y=402)])
            else:
                assert False, f"Unexpected label color: {label.color}"

    from tests import compare_projects
    compare_projects(output_ilp_path, sample_trained_ilp_path)


#######################################33

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

####################################3

    priority_executor.shutdown()

##################################################3333
if __name__ == "__main__":
    test_pixel_classification_workflow()
