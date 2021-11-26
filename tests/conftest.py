import datetime
import os
from pathlib import Path, PurePosixPath
from typing import Tuple

import pytest
import numpy as np
from ndstructs.point5D import Point5D
from webilastik.annotations.annotation import Annotation, Color

from webilastik.datasource import SkimageDataSource
from webilastik.filesystem.osfs import OsFs
from webilastik.libebrains.user_token import UserToken
from webilastik.filesystem.bucket_fs import BucketFs


@pytest.fixture(scope="session")
def ebrains_user_token() -> UserToken:
    return UserToken(
        access_token=os.environ["EBRAINS_ACCESS_TOKEN"]
    )

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
        path=Path("c_cells_1.png"),
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
