import datetime
from pathlib import PurePosixPath
from typing import Sequence, Tuple

import pytest
import numpy as np
from ndstructs.point5D import Point5D
from webilastik.annotations.annotation import Annotation, Color
from webilastik.classifiers.pixel_classifier import VigraPixelClassifier

from webilastik.datasource.skimage_datasource import SkimageDataSource
from webilastik.features.channelwise_fastfilters import GaussianSmoothing, HessianOfGaussianEigenvalues
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem.osfs import OsFs
from webilastik.libebrains.user_token import UserToken
from webilastik.filesystem.bucket_fs import BucketFs


@pytest.fixture(scope="session")
def ebrains_user_token() -> UserToken:
    return UserToken.get_global_token_or_raise()

@pytest.fixture(scope="session")
def bucket_fs(ebrains_user_token: UserToken) -> BucketFs:
    now = datetime.datetime.now()
    now_str = f"{now.year:02}y{now.month:02}m{now.day:02}d__{now.hour:02}h{now.minute:02}m{now.second:02}s"
    return BucketFs(
        bucket_name="hbp-image-service",
        prefix=PurePosixPath(f"/test-{now_str}"),
        ebrains_user_token=ebrains_user_token
    )

@pytest.fixture(scope="session")
def raw_data_source() -> SkimageDataSource:
    return SkimageDataSource(
        path=PurePosixPath("c_cells_1.png"),
        filesystem=OsFs("public/images/")
    )

@pytest.fixture(scope="session")
def pixel_annotations(raw_data_source: SkimageDataSource) -> Tuple[Annotation, ...]:
    return (
        Annotation.interpolate_from_points(
            voxels=[Point5D.zero(x=140, y=150), Point5D.zero(x=145, y=155)],
            color=Color(r=np.uint8(0), g=np.uint8(0), b=np.uint8(255)),
            raw_data=raw_data_source
        ),
        Annotation.interpolate_from_points(
            voxels=[Point5D.zero(x=238, y=101), Point5D.zero(x=229, y=139)],
            color=Color(r=np.uint8(0), g=np.uint8(0), b=np.uint8(255)),
            raw_data=raw_data_source
        ),
        Annotation.interpolate_from_points(
            voxels=[Point5D.zero(x=283, y=87), Point5D.zero(x=288, y=92)],
            color=Color(r=np.uint8(255), g=np.uint8(0), b=np.uint8(0)),
            raw_data=raw_data_source
        ),
        Annotation.interpolate_from_points(
            voxels=[Point5D.zero(x=274, y=168), Point5D.zero(x=256, y=191)],
            color=Color(r=np.uint8(255), g=np.uint8(0), b=np.uint8(0)),
            raw_data=raw_data_source
        ),
    )

@pytest.fixture
def feature_extractors() -> Sequence[IlpFilter]:
    return (
        GaussianSmoothing(sigma=0.3, axis_2d="z"),
        HessianOfGaussianEigenvalues(scale=0.7, axis_2d="z"),
    )

@pytest.fixture
def c_cells_pixel_classifier(
    pixel_annotations: Tuple[Annotation, ...],
    feature_extractors: Sequence[IlpFilter],
) -> VigraPixelClassifier[IlpFilter]:
    return VigraPixelClassifier.train(
        feature_extractors=feature_extractors,
        annotations=pixel_annotations,
    )