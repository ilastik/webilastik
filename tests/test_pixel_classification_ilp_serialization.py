from concurrent.futures import ProcessPoolExecutor
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from typing import List, Set

import h5py
import numpy as np
from ndstructs.point5D import Point5D

from webilastik.annotations.annotation import Annotation, Color
from webilastik.classic_ilastik.ilp import IlpFeatureSelectionsGroup
from webilastik.classic_ilastik.ilp.pixel_classification_ilp import IlpPixelClassificationWorkflowGroup
from webilastik.datasource.skimage_datasource import SkimageDataSource
from webilastik.features.ilp_filter import (
    IlpDifferenceOfGaussians,
    IlpGaussianGradientMagnitude,
    IlpGaussianSmoothing,
    IlpHessianOfGaussianEigenvalues,
    IlpLaplacianOfGaussian,
    IlpStructureTensorEigenvalues
)
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem.osfs import OsFs
from webilastik.scheduling.job import PriorityExecutor
from webilastik.ui.applet import dummy_prompt
from webilastik.utility.url import Protocol
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow


def test_feature_extractor_serialization():
    all_feature_extractors: List[IlpFilter] = []
    for scale in [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0]:
        all_feature_extractors.append(IlpGaussianSmoothing(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.append(IlpLaplacianOfGaussian(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.append(IlpGaussianGradientMagnitude(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.append(IlpDifferenceOfGaussians(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.append(IlpStructureTensorEigenvalues(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.append(IlpHessianOfGaussianEigenvalues(ilp_scale=scale, axis_2d="z"))

    feature_selection_group = IlpFeatureSelectionsGroup(feature_extractors=all_feature_extractors)
    tmp_file = tempfile.NamedTemporaryFile()
    with h5py.File(tmp_file.name, "w") as f:
        feature_selection_group.populate_group(f)

        parsed = IlpFeatureSelectionsGroup.parse(f)
        assert set(all_feature_extractors) == set(parsed.feature_extractors)

def test_pixel_classification_ilp_serialization():
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
        assert IlpGaussianSmoothing(ilp_scale=0.3, axis_2d="z") in loaded_feature_extractors
        assert IlpLaplacianOfGaussian(ilp_scale=0.7, axis_2d="z") in loaded_feature_extractors
        assert IlpGaussianGradientMagnitude(ilp_scale=1.0, axis_2d="z") in loaded_feature_extractors
        assert IlpDifferenceOfGaussians(ilp_scale=1.6, axis_2d="z") in loaded_feature_extractors
        assert IlpStructureTensorEigenvalues(ilp_scale=3.5, axis_2d="z") in loaded_feature_extractors
        assert IlpHessianOfGaussianEigenvalues(ilp_scale=5.0, axis_2d="z") in loaded_feature_extractors
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

    some_executor = ProcessPoolExecutor(max_workers=2)
    priority_executor = PriorityExecutor(executor=some_executor, max_active_job_steps=2)
    workflow = PixelClassificationWorkflow.from_ilp(
        allowed_protocols=[Protocol.FILE],
        executor=some_executor,
        priority_executor=priority_executor,
        ilp_path=output_ilp_path,
        on_async_change=lambda: None,
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