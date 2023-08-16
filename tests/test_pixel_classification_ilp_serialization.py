from concurrent.futures import ProcessPoolExecutor
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from typing import List, Set

import h5py
import numpy as np
from ndstructs.point5D import Point5D
from tests import get_project_root_dir

from webilastik.annotations.annotation import Annotation, Color
from webilastik.classic_ilastik.ilp import IlpFeatureSelectionsGroup
from webilastik.classic_ilastik.ilp.pixel_classification_ilp import IlpPixelClassificationWorkflowGroup
from webilastik.datasource.skimage_datasource import SkimageDataSource
from webilastik.features.ilp_filter import (
    IlpDifferenceOfGaussians,
    IlpFilterCollection,
    IlpGaussianGradientMagnitude,
    IlpGaussianSmoothing,
    IlpHessianOfGaussianEigenvalues,
    IlpLaplacianOfGaussian,
    IlpStructureTensorEigenvalues
)
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem.os_fs import OsFs
from webilastik.scheduling.job import PriorityExecutor
from webilastik.ui.applet import dummy_prompt
from webilastik.utility.url import Protocol
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow, WsPixelClassificationWorkflow

osfs = OsFs.create()
assert not isinstance(osfs, Exception)

def test_feature_extractor_serialization():
    all_feature_extractors: Set[IlpFilter] = set()
    for scale in [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0]:
        all_feature_extractors.add(IlpGaussianSmoothing(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.add(IlpLaplacianOfGaussian(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.add(IlpGaussianGradientMagnitude(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.add(IlpDifferenceOfGaussians(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.add(IlpStructureTensorEigenvalues(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.add(IlpHessianOfGaussianEigenvalues(ilp_scale=scale, axis_2d="z"))

    filter_collection = IlpFilterCollection(all_feature_extractors)
    feature_selection_group = IlpFeatureSelectionsGroup(feature_extractors=filter_collection)
    tmp_file = tempfile.NamedTemporaryFile()
    with h5py.File(tmp_file.name, "w") as f:
        feature_selection_group.populate_group(f)

        parsed = IlpFeatureSelectionsGroup.parse(f)
        assert filter_collection == parsed.feature_extractors

def test_pixel_classification_ilp_serialization():
    input_fs = OsFs.create()
    assert not isinstance(input_fs, Exception), str(input_fs)
    sample_trained_ilp_path = get_project_root_dir() / "tests/projects/TrainedPixelClassification.ilp"

    output_fs = OsFs.create_scratch_dir();
    assert not isinstance(output_fs, Exception)
    output_ilp_path = PurePosixPath("rewritten.ilp")

    sample_workflow_data = IlpPixelClassificationWorkflowGroup.from_file(ilp_fs=input_fs, path=sample_trained_ilp_path)
    assert not isinstance(sample_workflow_data, Exception), str(sample_workflow_data)

    write_result = output_fs.create_file(path=output_ilp_path, contents=sample_workflow_data.to_h5_file_bytes())
    assert not isinstance(write_result, Exception)
    write_result = output_fs.transfer_file(source_fs=input_fs, source_path=sample_trained_ilp_path.parent / "c_cells_1.png", target_path=PurePosixPath("c_cells_1.png"))
    assert not isinstance(write_result, Exception)

    reloaded_data = IlpPixelClassificationWorkflowGroup.from_file(ilp_fs=output_fs, path=output_ilp_path)
    assert not isinstance(reloaded_data, Exception), str(reloaded_data)

    loaded_feature_extractors = reloaded_data.FeatureSelections.feature_extractors
    assert IlpGaussianSmoothing(ilp_scale=0.3, axis_2d="z") in loaded_feature_extractors.filters
    assert IlpLaplacianOfGaussian(ilp_scale=0.7, axis_2d="z") in loaded_feature_extractors.filters
    assert IlpGaussianGradientMagnitude(ilp_scale=1.0, axis_2d="z") in loaded_feature_extractors.filters
    assert IlpDifferenceOfGaussians(ilp_scale=1.6, axis_2d="z") in loaded_feature_extractors.filters
    assert IlpStructureTensorEigenvalues(ilp_scale=3.5, axis_2d="z") in loaded_feature_extractors.filters
    assert IlpHessianOfGaussianEigenvalues(ilp_scale=5.0, axis_2d="z") in loaded_feature_extractors.filters
    assert len(loaded_feature_extractors.filters) == 6

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

    some_executor = ProcessPoolExecutor(max_workers=2)
    priority_executor = PriorityExecutor(executor=some_executor, max_active_job_steps=2)
    workflow_ilp_group = IlpPixelClassificationWorkflowGroup.from_file(ilp_fs=output_fs, path=output_ilp_path)
    assert not isinstance(workflow_ilp_group, Exception), str(workflow_ilp_group)
    workflow = PixelClassificationWorkflow.from_ilp(
        workflow_group=workflow_ilp_group,
        on_async_change=lambda: None,
        executor=some_executor,
        priority_executor=priority_executor,
    )
    assert not isinstance(workflow, Exception)
    print(f"These are the deserialized brush strokes:")

    from pprint import pprint
    pprint(workflow.brushing_applet.label_classes())

    annotation_raw_data = workflow.brushing_applet.labels()[0].annotations[0].raw_data
    expected_annotation1 = Annotation.from_voxels(
        voxels=[Point5D(x=200, y=200), Point5D(x=201, y=201), Point5D(x=202, y=202)],
        raw_data=annotation_raw_data,
    )
    expected_annotation2 = Annotation.from_voxels(
        voxels=[Point5D(x=400, y=400), Point5D(x=401, y=401), Point5D(x=402, y=402)],
        raw_data=annotation_raw_data,
    )

    assert set(a for annotations in workflow.brushing_applet.label_classes().values() for a in annotations) == set([expected_annotation1, expected_annotation2])

    res = workflow.brushing_applet.remove_annotation(user_prompt=dummy_prompt, label_name="Label 1", annotation=expected_annotation1)
    print(res)
    pprint(workflow.brushing_applet.label_classes())



    priority_executor.shutdown()
    some_executor.shutdown()

    # from tests import compare_projects
    # compare_projects(output_ilp_path, sample_trained_ilp_path)

if __name__ == "__main__":
    test_feature_extractor_serialization()
    test_pixel_classification_ilp_serialization()