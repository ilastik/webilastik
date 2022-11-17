from functools import partial
from pathlib import PurePosixPath
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from tests import get_sample_c_cells_datasource, get_test_output_bucket_fs
from webilastik.datasink import IDataSinkWriter
from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksSink
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksScale, RawEncoder
from webilastik.datasource import DataRoi


def _write_data(tile: DataRoi, sink_writer: IDataSinkWriter):
    print(f"Writing {tile}")
    sink_writer.write(tile.retrieve())

def test_bucket_read_write():
    raw_data_source = get_sample_c_cells_datasource()
    bucket_fs = get_test_output_bucket_fs()

    precomp_path = PurePosixPath("c_cells_1.precomputed")
    sink = PrecomputedChunksSink(
        filesystem=bucket_fs,
        path=precomp_path,
        scale_key=PurePosixPath("exported_data"),
        tile_shape=raw_data_source.tile_shape,
        interval=raw_data_source.interval,
        resolution=raw_data_source.spatial_resolution,
        encoding=RawEncoder(),
        dtype=raw_data_source.dtype,
    )

    sink_writer = sink.open()
    assert not isinstance(sink_writer, Exception)

    assert bucket_fs.exists(precomp_path.joinpath("info").as_posix())
    assert not bucket_fs.exists(precomp_path.joinpath("i_dont_exist").as_posix())

    with ProcessPoolExecutor() as executor:
        _ = list(executor.map(
            partial(_write_data, sink_writer=sink_writer),
            raw_data_source.roi.get_datasource_tiles()
        ))

    data_proxy_source = PrecomputedChunksDataSource(
        path=precomp_path,
        filesystem=bucket_fs,
        resolution=(raw_data_source.spatial_resolution)
    )

    retrieved_data = data_proxy_source.retrieve()
    assert np.all(retrieved_data.raw("yxc") == raw_data_source.retrieve().raw("yxc"))

if __name__ == "__main__":
    test_bucket_read_write()