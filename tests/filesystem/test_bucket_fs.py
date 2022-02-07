# pyright:

from functools import partial
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from webilastik.datasink import DataSink
from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksSink
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksInfo, PrecomputedChunksScale, RawEncoder

from webilastik.filesystem.bucket_fs import BucketFs
from webilastik.datasource import DataRoi, SkimageDataSource


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

    assert bucket_fs.exists(precomp_path.joinpath("info").as_posix())
    assert not bucket_fs.exists(precomp_path.joinpath("i_dont_exist").as_posix())

    with ProcessPoolExecutor() as executor:
        _ = list(executor.map(
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
