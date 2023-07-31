from pathlib import PurePosixPath
from typing import List, Set

import h5py
import numpy as np

import tests
from webilastik.classic_ilastik.ilp.pixel_classification_ilp import IlpPixelClassificationGroup
from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasource import FsDataSource
from webilastik.annotations import Color
from webilastik.features.ilp_filter import (
    IlpFilter,
    IlpGaussianSmoothing,
    IlpLaplacianOfGaussian,
    IlpGaussianGradientMagnitude,
    IlpDifferenceOfGaussians,
    IlpStructureTensorEigenvalues,
    IlpHessianOfGaussianEigenvalues,
)
from webilastik.filesystem.os_fs import OsFs
from ndstructs.point5D import Point5D

def test_pixel_classifier():
    default_scales = [0.7, 1.0, 1.6, 3.5, 5.0, 10.0]

    feature_extractors: List[IlpFilter] = [
        *[IlpGaussianSmoothing(ilp_scale=scale, axis_2d="z") for scale in default_scales],
        *[IlpLaplacianOfGaussian(ilp_scale=scale, axis_2d="z") for scale in default_scales],
        *[IlpGaussianGradientMagnitude(ilp_scale=scale, axis_2d="z") for scale in default_scales],
        *[IlpDifferenceOfGaussians(ilp_scale=scale, axis_2d="z") for scale in default_scales],
        *[IlpStructureTensorEigenvalues(ilp_scale=scale, axis_2d="z") for scale in default_scales],
        *[IlpHessianOfGaussianEigenvalues(ilp_scale=scale, axis_2d="z") for scale in default_scales],
    ]
    labels = tests.get_sample_c_cells_pixel_annotations()
    classifier = VigraPixelClassifier.train(
        feature_extractors=feature_extractors,
        label_classes=[label.annotations for label in labels],
    )
    if isinstance(classifier, Exception):
        raise classifier

    datasource = labels[0].annotations[0].raw_data
    assert isinstance(datasource, FsDataSource)

    predictions1 = classifier(datasource.roi)

    pixel_classif_group = IlpPixelClassificationGroup(
        classifier=classifier,
        labels=labels,
    )

    scratch_fs = OsFs.create_scratch_dir()
    assert not isinstance(scratch_fs, Exception)

    with h5py.File(scratch_fs.geturl(PurePosixPath("/my_classifier_dump.h5")).path, "w") as f:
        serialized_classifier_group = f.create_group("my_group")
        pixel_classif_group.populate_group(serialized_classifier_group)

        loaded_classification_group = IlpPixelClassificationGroup.parse(
            group=serialized_classifier_group,
            raw_data_sources={0: datasource}
        )
    loaded_classifier = loaded_classification_group.classifier
    assert loaded_classifier is not None

    for label_index, label in enumerate(loaded_classification_group.labels):
        loaded_points: Set[Point5D] = set()
        for a in label.annotations:
            loaded_points.update(a.to_points())
        for a in labels[label_index].annotations:
            for point in a.to_points():
                assert point in loaded_points
                loaded_points.remove(point)
        assert len(loaded_points) == 0

    predictions2 = loaded_classifier(datasource.roi)
    assert predictions2 == predictions1



if __name__ == "__main__":
    test_pixel_classifier()