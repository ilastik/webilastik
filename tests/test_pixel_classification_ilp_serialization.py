from pathlib import Path
import shutil
import tempfile
from typing import List, Set
import uuid

import h5py
import numpy as np
from ndstructs.point5D import Point5D

from webilastik.annotations.annotation import Color
from webilastik.classic_ilastik.ilp import IlpFeatureSelectionsGroup
from webilastik.classic_ilastik.ilp.pixel_classification_ilp import IlpPixelClassificationWorkflowGroup
from webilastik.features.channelwise_fastfilters import (
    DifferenceOfGaussians,
    GaussianGradientMagnitude,
    GaussianSmoothing,
    HessianOfGaussianEigenvalues,
    LaplacianOfGaussian,
    StructureTensorEigenvalues
)
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem.osfs import OsFs
from webilastik.utility.url import Protocol


def test_feature_extractor_serialization():
    all_feature_extractors: List[IlpFilter] = []
    for scale in [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0]:
        all_feature_extractors.append(GaussianSmoothing(sigma=scale, axis_2d="z"))
        all_feature_extractors.append(LaplacianOfGaussian(scale=scale, axis_2d="z"))
        all_feature_extractors.append(GaussianGradientMagnitude(sigma=scale, axis_2d="z"))
        all_feature_extractors.append(DifferenceOfGaussians(sigma0=scale, sigma1=scale * 0.66, axis_2d="z"))
        all_feature_extractors.append(StructureTensorEigenvalues(innerScale=scale, outerScale=0.5 * scale, axis_2d="z"))
        all_feature_extractors.append(HessianOfGaussianEigenvalues(scale=scale, axis_2d="z"))

    feature_selection_group = IlpFeatureSelectionsGroup(feature_extractors=all_feature_extractors)
    tmp_file = tempfile.NamedTemporaryFile()
    print(tmp_file.name)
    # tmp_file_name = f"/tmp/feature_selection_{uuid.uuid4()}.h5"
    with h5py.File(tmp_file.name, "w") as f:
        feature_selection_group.populate_group(f)

        parsed = IlpFeatureSelectionsGroup.parse(f)
        assert set(all_feature_extractors) == set(parsed.feature_extractors)
    print("yay!")

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

print(f"what's my anme?????? {__name__}")

if __name__ == "__main__":
    test_feature_extractor_serialization()
    test_pixel_classification_ilp_serialization()