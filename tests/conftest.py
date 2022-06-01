import datetime
from pathlib import PurePosixPath
from typing import Dict, Sequence, Tuple

import pytest
from webilastik.annotations.annotation import Annotation, Color
from webilastik.classifiers.pixel_classifier import VigraPixelClassifier

from webilastik.datasource.skimage_datasource import SkimageDataSource
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem.osfs import OsFs
from webilastik.libebrains.user_token import UserToken
from webilastik.filesystem.bucket_fs import BucketFs
import tests


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
def pixel_annotations(raw_data_source: SkimageDataSource) -> Dict[Color, Tuple[Annotation, ...]]:
    return {label.color: tuple(label.annotations) for label in tests.get_sample_c_cells_pixel_annotations()}

@pytest.fixture
def feature_extractors() -> Sequence[IlpFilter]:
    return tests.get_sample_feature_extractors()

@pytest.fixture
def c_cells_pixel_classifier(
    pixel_annotations: Tuple[Annotation, ...],
    feature_extractors: Sequence[IlpFilter],
) -> VigraPixelClassifier[IlpFilter]:
    return tests.get_sample_c_cells_pixel_classifier()