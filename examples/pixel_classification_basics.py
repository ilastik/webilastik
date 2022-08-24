#!/usr/bin/env python

#pyright: strict

# in real applications, select your caching and executor_get implementation via PYTHONPATH
import sys
from pathlib import Path, PurePosixPath
project_root_dir = Path(__file__).parent.parent
sys.path.insert(0, project_root_dir.as_posix())
sys.path.insert(0, project_root_dir.joinpath('caching/no_cache').as_posix())
sys.path.insert(0, project_root_dir.joinpath('executor_getters/default').as_posix())


from ndstructs.point5D import Interval5D, Point5D
from ndstructs.array5D import Array5D
import numpy as np

from webilastik.annotations.annotation import Annotation
from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksScaleSink
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksScale, RawEncoder
from webilastik.datasource.skimage_datasource import SkimageDataSource
from webilastik.features.ilp_filter import IlpGaussianSmoothing
from webilastik.filesystem.osfs import OsFs


# some sample data to work on. DataSource implementations are tile-based.
data_source = SkimageDataSource(
    filesystem=OsFs(project_root_dir.as_posix()), #filesystem could also be HttpFs, BucketFs, etc
    path=PurePosixPath("public/images/c_cells_1.png")
)

feature_extractors = [
     #computes in 2D, slicing along the axis_2d. set axis_2d to None to compute in 3D
    IlpGaussianSmoothing(ilp_scale=0.3, axis_2d="z"),
    IlpGaussianSmoothing(ilp_scale=0.7, axis_2d="z"),
    IlpGaussianSmoothing(ilp_scale=1.0, axis_2d="z"),
    IlpGaussianSmoothing(ilp_scale=1.6, axis_2d="z"),
    IlpGaussianSmoothing(ilp_scale=3.5, axis_2d="z"),
    IlpGaussianSmoothing(ilp_scale=5.0, axis_2d="z"),
    IlpGaussianSmoothing(ilp_scale=10.0, axis_2d="z"),
]

label_classes = [
    #first label/class
    [
        Annotation.interpolate_from_points(
            voxels=[Point5D.zero(x=140, y=150), Point5D.zero(x=145, y=155)],
            raw_data=data_source # All Annotations know what they have annotated
        ),
        Annotation.interpolate_from_points(
            voxels=[Point5D.zero(x=238, y=101), Point5D.zero(x=229, y=139)],
            raw_data=data_source
        ),
    ],
    #second label/class
    [
        Annotation.interpolate_from_points(
            voxels=[Point5D.zero(x=283, y=87), Point5D.zero(x=288, y=92)],
            raw_data=data_source
        ),
        Annotation.interpolate_from_points(
            voxels=[Point5D.zero(x=274, y=168), Point5D.zero(x=256, y=191)],
            raw_data=data_source
        ),
    ]
]

classifier = VigraPixelClassifier.train(
    feature_extractors=feature_extractors,
    label_classes=label_classes
)
 # many methods return SomeValue | Exception so that the type checker
 # can warn about unhandled exceptions
assert not isinstance(classifier, Exception)


# we will output to neuroglancer's Precomputed Chunks format
# https://github.com/google/neuroglancer/tree/master/src/neuroglancer/datasource/precomputed
output_interval: Interval5D = classifier.get_expected_roi(data_source.roi)
predictions_data_sink = PrecomputedChunksScaleSink(
    filesystem=OsFs("/tmp"),
    dtype=np.dtype("float32"),
    info_dir=PurePosixPath("my_exported_data"),
    num_channels=classifier.num_classes,
    scale=PrecomputedChunksScale(
        key=PurePosixPath("1_1_1"),
        size=(output_interval.shape.x, output_interval.shape.y, output_interval.shape.z),
        resolution=(1,1,1),
        voxel_offset=(output_interval.start.x, output_interval.start.y, output_interval.start.z),
        chunk_sizes=(
            (data_source.tile_shape.x, data_source.tile_shape.y, data_source.tile_shape.z),
        ),
        encoding=RawEncoder()
    )
)
 #creates info file on disk plus the "my_exported_data" dir, making us ready to write
sink_writer = predictions_data_sink.create()
assert not isinstance(sink_writer, Exception)

# predict on independent tiles. You could run this with e.g. concurrent.futures.Executor
for lazy_tile in data_source.roi.get_datasource_tiles():
    predictions: Array5D = classifier(lazy_tile) #if you need the raw numpy array, call .e.g predictions.raw("yx")
    #predictions.as_uint8().show_channels()
    sink_writer.write(predictions)
