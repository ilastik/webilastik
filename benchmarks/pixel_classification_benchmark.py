# pyright: strict

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, wait as wait_futures
from pathlib import Path, PurePosixPath
from typing import List, Sequence
import time
import argparse
import re
import os

import numpy as np
from ndstructs.point5D import Point5D

from webilastik.annotations.annotation import Annotation, Color
from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasource import DataSource
from webilastik.features.channelwise_fastfilters import get_axis_2d
from webilastik.features.ilp_filter import (
    IlpGaussianSmoothing,
    IlpLaplacianOfGaussian,
    IlpGaussianGradientMagnitude,
    IlpDifferenceOfGaussians,
    IlpStructureTensorEigenvalues,
    IlpHessianOfGaussianEigenvalues,
)
from webilastik.features.feature_extractor import FeatureExtractor, JsonableFeatureExtractor
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.filesystem.osfs import OsFs
from webilastik.scheduling import SerialExecutor


feature_extractors_classes = {
    "GaussianSmoothing": IlpGaussianSmoothing,
    "LaplacianOfGaussian": IlpLaplacianOfGaussian,
    "GaussianGradientMagnitude": IlpGaussianGradientMagnitude,
    "DifferenceOfGaussians": IlpDifferenceOfGaussians,
    "StructureTensorEigenvalues": IlpStructureTensorEigenvalues,
    "HessianOfGaussianEigenvalues": IlpHessianOfGaussianEigenvalues,
}

def feature_extractor_from_arg(arg: str) -> FeatureExtractor:
    extractor_class_name_regex = r"(?P<extractor_class_name>\w+)"
    open_parens_regex = r"\("
    scale_regex = r"(?P<scale>[0-9]+\.[0-9]+)"
    axis_2d_regex = r'( *, *axis_2d *="(?P<axis_2d>[xyzt])")?'
    close_parens_regex = r"\)"
    regex = re.compile(extractor_class_name_regex + open_parens_regex + scale_regex + axis_2d_regex + close_parens_regex)

    match = regex.fullmatch(arg)
    if match is None:
        raise Exception(f"Bad feature extractor parameter: {arg}")

    class_name = match.group("extractor_class_name")
    scale = match.group("scale")
    axis_2d = get_axis_2d(match.group("axis_2d") or "z")
    return feature_extractors_classes[class_name](ilp_scale=float(scale), axis_2d=axis_2d)

default_scales = [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0]

argparser = argparse.ArgumentParser()
_ = argparser.add_argument(
    "--extractors",
    nargs="+",
    required=False,
    type=feature_extractor_from_arg,
    default=[
        *[IlpGaussianSmoothing(ilp_scale=s, axis_2d="z") for s in default_scales],
        *[IlpLaplacianOfGaussian(ilp_scale=s, axis_2d="z") for s in default_scales],
        *[IlpGaussianGradientMagnitude(ilp_scale=s, axis_2d="z") for s in default_scales],
        *[IlpDifferenceOfGaussians(ilp_scale=s, axis_2d="z") for s in default_scales],
        *[IlpStructureTensorEigenvalues(ilp_scale=s, axis_2d="z") for s in default_scales],
        *[IlpHessianOfGaussianEigenvalues(ilp_scale=s, axis_2d="z") for s in default_scales],
    ]
)
args = argparser.parse_args()

selected_feature_extractors: Sequence[JsonableFeatureExtractor] = args.extractors
print(f"Extractors:")
for ex in selected_feature_extractors:
    print(ex.to_json_value())

mouse_datasources: List[DataSource] = [
    PrecomputedChunksDataSource(
        filesystem=OsFs(Path(__file__).joinpath("../../public/images/").as_posix()),
        path=PurePosixPath(f"mouse{i}.precomputed"),
        resolution=(1,1,1)
    ) for i in range(1, 3 + 1)
]

class1_annotations = [
    Annotation.from_voxels(
        voxels=[
                Point5D(x=2156, y=1326, z=0),
                Point5D(x=2157, y=1326, z=0),
                Point5D(x=2157, y=1327, z=0),
                Point5D(x=2157, y=1328, z=0),
                Point5D(x=2157, y=1329, z=0),
                Point5D(x=2157, y=1330, z=0),
                Point5D(x=2158, y=1330, z=0),
                Point5D(x=2159, y=1330, z=0),
                Point5D(x=2159, y=1331, z=0),
                Point5D(x=2160, y=1331, z=0),
                Point5D(x=2161, y=1331, z=0),
                Point5D(x=2162, y=1331, z=0),
                Point5D(x=2163, y=1331, z=0),
                Point5D(x=2163, y=1332, z=0),
                Point5D(x=2164, y=1332, z=0),
                Point5D(x=2164, y=1333, z=0),
                Point5D(x=2164, y=1334, z=0),
                Point5D(x=2163, y=1334, z=0),
                Point5D(x=2162, y=1334, z=0),
                Point5D(x=2161, y=1334, z=0),
                Point5D(x=2160, y=1334, z=0),
                Point5D(x=2159, y=1334, z=0),
                Point5D(x=2158, y=1334, z=0),
                Point5D(x=2158, y=1335, z=0),
                Point5D(x=2157, y=1335, z=0),
                Point5D(x=2156, y=1336, z=0),
                Point5D(x=2155, y=1336, z=0),
                Point5D(x=2154, y=1336, z=0),
                Point5D(x=2153, y=1336, z=0),
                Point5D(x=2152, y=1336, z=0),
                Point5D(x=2152, y=1335, z=0),
                Point5D(x=2151, y=1334, z=0),
                Point5D(x=2151, y=1333, z=0),
                Point5D(x=2150, y=1333, z=0),
                Point5D(x=2150, y=1332, z=0),
        ],
        raw_data=mouse_datasources[0],
    ),
]

class_2_annotations = [
    Annotation.from_voxels(
        voxels=[
            Point5D(x=2177, y=1316, z=0),
            Point5D(x=2177, y=1317, z=0),
            Point5D(x=2177, y=1318, z=0),
            Point5D(x=2177, y=1319, z=0),
            Point5D(x=2178, y=1319, z=0),
            Point5D(x=2178, y=1320, z=0),
            Point5D(x=2178, y=1321, z=0),
            Point5D(x=2178, y=1322, z=0),
            Point5D(x=2179, y=1322, z=0),
            Point5D(x=2179, y=1323, z=0),
            Point5D(x=2179, y=1324, z=0),
            Point5D(x=2180, y=1324, z=0),
            Point5D(x=2180, y=1325, z=0),
            Point5D(x=2181, y=1325, z=0),
            Point5D(x=2181, y=1326, z=0),
            Point5D(x=2182, y=1326, z=0),
            Point5D(x=2182, y=1327, z=0),
            Point5D(x=2183, y=1327, z=0),
            Point5D(x=2183, y=1328, z=0),
            Point5D(x=2184, y=1328, z=0),
            Point5D(x=2185, y=1328, z=0),
            Point5D(x=2186, y=1328, z=0),
            Point5D(x=2187, y=1328, z=0),
            Point5D(x=2188, y=1328, z=0),
            Point5D(x=2188, y=1329, z=0),
            Point5D(x=2189, y=1329, z=0),
            Point5D(x=2190, y=1329, z=0),
            Point5D(x=2191, y=1329, z=0),
            Point5D(x=2192, y=1329, z=0),
            Point5D(x=2192, y=1328, z=0),
            Point5D(x=2193, y=1328, z=0),
            Point5D(x=2194, y=1328, z=0),
            Point5D(x=2194, y=1327, z=0),
        ],
        raw_data=mouse_datasources[0]
    ),
]

colors = [
    Color(r=np.uint8(255)),
    Color(g=np.uint8(255)),
]
# for ca, color in zip([class1_annotations, class_2_annotations], colors):
#     for a in ca:
#         a.show(color)


t = time.time()
classifier = VigraPixelClassifier.train(feature_extractors=selected_feature_extractors, label_classes=[
    class1_annotations,
    class_2_annotations
])
if isinstance(classifier, Exception):
    raise classifier
print(f"Trained classifier in {time.time() - t} seconds")


ds = mouse_datasources[0]

executor_creators = [
    lambda: ProcessPoolExecutor(max_workers=os.cpu_count()),
    lambda: ThreadPoolExecutor(max_workers=os.cpu_count()),
    lambda: SerialExecutor()
]
for executor_creator in executor_creators:
    t = time.time()
    with executor_creator() as executor:
        print(f"Executor {executor.__class__.__name__} created in {time.time() - t}s")
        t = time.time()
        futs = [executor.submit(classifier, tile) for tile in ds.roi.default_split()]
        _ = wait_futures(futs)
        print(f"Predicted image sized {ds.shape} with {executor.__class__.__name__} in {time.time() - t}s")
        t = time.time()
