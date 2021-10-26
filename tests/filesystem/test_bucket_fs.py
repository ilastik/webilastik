from functools import partial
import random
from pathlib import Path, PurePosixPath
import os
import datetime
from concurrent.futures import ProcessPoolExecutor

import pytest
import numpy as np
from fs.osfs import OSFS
from webilastik import filesystem
from webilastik.datasink import DataSink
from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksSink
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksInfo, PrecomputedChunksScale, RawEncoder
from webilastik.filesystem.osfs import OsFs

from webilastik.filesystem.bucket_fs import BucketFs
from webilastik.libebrains.user_token import UserToken
from webilastik.datasource import DataRoi, DataSource, SkimageDataSource
from webilastik.filesystem.http_fs import HttpFs
from webilastik.utility.url import Url

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

def _write_data(tile: DataRoi, sink: DataSink):
    print(f"Writing {tile}")
    sink.write(tile.retrieve())

def test_bucket_read_write(raw_data_source: SkimageDataSource, bucket_fs: BucketFs):
    precomp_path = Path("c_cells_1.precomputed")
    sink = PrecomputedChunksSink.create(
        base_path=precomp_path,
        filesystem=bucket_fs,
        info=PrecomputedChunksInfo(
            data_type=raw_data_source.dtype,
            type_="image",
            num_channels=raw_data_source.shape.c,
            scales=tuple([
                PrecomputedChunksScale(
                    key=Path("exported_data"),
                    size=(raw_data_source.shape.x, raw_data_source.shape.y, raw_data_source.shape.z),
                    chunk_sizes=tuple([
                        (raw_data_source.tile_shape.x, raw_data_source.tile_shape.y, raw_data_source.tile_shape.z)
                    ]),
                    encoding=RawEncoder(),
                    voxel_offset=(raw_data_source.location.x, raw_data_source.location.y, raw_data_source.location.z),
                    resolution=raw_data_source.spatial_resolution
                )
            ]),
        )
    ).scale_sinks[0]

    with ProcessPoolExecutor() as executor:
        list(executor.map(
            partial(_write_data, sink=sink),
            raw_data_source.roi.get_datasource_tiles()
        ))

    data_proxy_source = PrecomputedChunksDataSource(
        path=precomp_path,
        filesystem=bucket_fs,
        resolution=(raw_data_source.spatial_resolution)
    )

    retrieved_data = data_proxy_source.retrieve()
    assert np.all(retrieved_data.raw("yxc") == raw_data_source.retrieve().raw("yxc"))


# test_bucket_read_write(
#     raw_data_source=raw_data_source(),
#     bucket_fs=bucket_fs(ebrains_user_token())
# )