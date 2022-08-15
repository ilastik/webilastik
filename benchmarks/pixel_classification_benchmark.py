# pyright: strict

from concurrent.futures import Executor, Future, wait as wait_futures
from functools import partial
from pathlib import Path, PurePosixPath
from typing import Any, List, Sequence
import time
import argparse
import re
import sys

from ndstructs.point5D import Point5D

from webilastik.annotations.annotation import Annotation
from webilastik.classifiers.pixel_classifier import PixelClassifier, VigraPixelClassifier
from webilastik.datasource import DataRoi, DataSource
from webilastik.datasource.skimage_datasource import SkimageDataSource
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

from executor_getter import get_executor

feature_extractors_classes = {
    "GaussianSmoothing": IlpGaussianSmoothing,
    "LaplacianOfGaussian": IlpLaplacianOfGaussian,
    "GaussianGradientMagnitude": IlpGaussianGradientMagnitude,
    "DifferenceOfGaussians": IlpDifferenceOfGaussians,
    "StructureTensorEigenvalues": IlpStructureTensorEigenvalues,
    "HessianOfGaussianEigenvalues": IlpHessianOfGaussianEigenvalues,
}

default_scales = [0.7, 1.0, 1.6, 3.5, 5.0, 10.0]

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


def compute_tile(classifier: PixelClassifier[Any], roi: DataRoi):
    print(f"Predicting on {roi}")
    _ = classifier(roi)#.as_uint8(normalized=True).show_channels()

if __name__ == "__main__":

    argparser = argparse.ArgumentParser()
    _ = argparser.add_argument(
        "--extractors",
        nargs="+",
        required=False,
        type=feature_extractor_from_arg,
        default=[IlpGaussianSmoothing(ilp_scale=0.3, axis_2d="z")] + [
            extractor_class(ilp_scale=scale, axis_2d="z")
            for extractor_class in feature_extractors_classes.values()
            for scale in default_scales
        ]
    )
    _ = argparser.add_argument(
        "--datasource",
        choices=["brain", "c_cells"],
        default="brain"
    )
    _ = argparser.add_argument(
        "--num-tiles"
    )

    args = argparser.parse_args()

    executor: Executor = get_executor(hint="server_tile_handler")

    selected_feature_extractors: Sequence[JsonableFeatureExtractor] = args.extractors
    num_tiles = None if args.num_tiles is None else int(args.num_tiles)

    mouse_datasources: List[DataSource] = [
        PrecomputedChunksDataSource(
            filesystem=OsFs(Path(__file__).joinpath("../../public/images/").as_posix()),
            path=PurePosixPath(f"mouse{i}.precomputed"),
            resolution=(1,1,1)
        ) for i in range(1, 3 + 1)
    ]

    if args.datasource == "brain":
        datasource = PrecomputedChunksDataSource(
            filesystem=OsFs(Path(__file__).joinpath("../../public/images/").as_posix()),
            path=PurePosixPath(f"mouse1.precomputed"),
            resolution=(1,1,1)
        )
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
    elif args.datasource == "c_cells":
        datasource = SkimageDataSource(
            filesystem=OsFs(Path(__file__).joinpath("../../public/images/").as_posix()),
            path=PurePosixPath("c_cells_1.png")
        )
        class1_annotations = [
            Annotation.interpolate_from_points(
                voxels=[Point5D.zero(x=140, y=150), Point5D.zero(x=145, y=155)],
                raw_data=datasource
            ),
            Annotation.interpolate_from_points(
                voxels=[Point5D.zero(x=238, y=101), Point5D.zero(x=229, y=139)],
                raw_data=datasource
            ),
        ]
        class_2_annotations = [
            Annotation.interpolate_from_points(
                voxels=[Point5D.zero(x=283, y=87), Point5D.zero(x=288, y=92)],
                raw_data=datasource
            ),
            Annotation.interpolate_from_points(
                voxels=[Point5D.zero(x=274, y=168), Point5D.zero(x=256, y=191)],
                raw_data=datasource
            ),
        ]
    else:
        raise Exception(f"Bad datasource: {args.datasource}")

    # colors = [
    #     Color(r=np.uint8(255)),
    #     Color(g=np.uint8(255)),
    # ]
    # for ca, color in zip([class1_annotations, class_2_annotations], colors):
    #     for a in ca:
    #         a.show(color)


    # roi = DataRoi(datasource=datasource, x=(100,200), y=(100,200), c=datasource.interval.c)
    # classifier(roi).as_uint8(normalized=True).show_channels()
    # exit(1)

    print(f"Extractors:")
    for fe in selected_feature_extractors:
        print(fe.to_json_value())

    t = time.time()
    classifier = VigraPixelClassifier.train(
        feature_extractors=selected_feature_extractors,
        label_classes=[
            class1_annotations,
            class_2_annotations
        ],
        random_seed=7919,
    )
    print(f"Trained classifier in {time.time() - t} seconds")
    if isinstance(classifier, Exception):
        raise classifier
    f = partial(compute_tile, classifier)

    t = time.time()
    futs: "List[Future[Any]]" = []

    requested_num_tiles = num_tiles or datasource.roi.get_num_tiles(tile_shape=datasource.tile_shape)
    # for tile in datasource.roi.get_datasource_tiles():
    #     _ = tile.retrieve() #prefetch
    for tile in datasource.roi.get_datasource_tiles():
        if len(futs) >= requested_num_tiles:
            break
        futs.append(executor.submit(f, tile))
        print(".", end="")
    _ = wait_futures(futs)
    print(f"ARGV: {sys.argv}")
    print(f"[{executor.__class__.__name__}] Predicted {len(futs)} tiles sized {datasource.tile_shape} in {time.time() - t}s")
