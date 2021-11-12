import datetime
import os
from pathlib import Path, PurePosixPath

import pytest

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
