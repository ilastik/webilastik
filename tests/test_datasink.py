#pyright: strict
from tests import create_tmp_dir
from webilastik.filesystem.os_fs import OsFs
from pathlib import PurePosixPath

import numpy as np
from ndstructs.point5D import Point5D, Shape5D
from ndstructs.array5D import Array5D

from webilastik.datasink.n5_dataset_sink import N5DataSink
from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksSink
from webilastik.datasource import DataRoi
from webilastik.datasource.array_datasource import ArrayDataSource
from webilastik.datasource.n5_datasource import N5DataSource
from webilastik.datasource.precomputed_chunks_info import RawEncoder
from webilastik.datasource.n5_attributes import RawCompressor



data = Array5D(np.arange(20 * 10 * 7).reshape(20, 10, 7), axiskeys="xyz") # pyright: ignore [reportUnknownMemberType]
data.setflags(write=False)

datasource = ArrayDataSource(data=data, tile_shape=Shape5D(x=10, y=10))

def test_n5_datasink():
    tmp_path = create_tmp_dir(prefix="test_n5_datasink")
    fs = OsFs.create()
    assert not isinstance(fs, Exception)
    sink = N5DataSink(
        filesystem=fs,
        path=tmp_path / "test_n5_datasink.n5/data",
        c_axiskeys=data.axiskeys, #FIXME: double check this
        compressor=RawCompressor(),
        dtype=datasource.dtype,
        interval=datasource.interval,
        tile_shape=Shape5D(x=10, y=10),
    )
    sink_writer = sink.open()
    assert not isinstance(sink_writer, Exception)
    for tile in DataRoi(datasource).split(sink.tile_shape):
        writing_result = sink_writer.write(tile.retrieve())
        assert not isinstance(writing_result, Exception)

    n5ds = N5DataSource.try_load(filesystem=sink.filesystem, path=sink.path)
    assert not isinstance(n5ds, Exception), str(n5ds)
    saved_data = n5ds.retrieve()
    assert saved_data == data

def test_distributed_n5_datasink():
    tmp_path = create_tmp_dir(prefix="test_distributed_n5_datasink")
    filesystem = OsFs.create()
    assert not isinstance(filesystem, Exception)
    path = tmp_path / "test_distributed_n5_datasink.n5/data"
    sink = N5DataSink(
        filesystem=filesystem,
        path=path,
        c_axiskeys=data.axiskeys, #FIXME: double check this
        compressor=RawCompressor(),
        dtype=datasource.dtype,
        interval=datasource.interval,
        tile_shape=datasource.tile_shape,
    )
    sink_writer = sink.open()
    assert not isinstance(sink_writer, Exception), str(sink_writer)
    sink_writers = [sink_writer] * 4

    for idx, piece in enumerate(DataRoi(datasource).default_split()):
        sink = sink_writers[idx % len(sink_writers)]
        writing_result = sink.write(piece.retrieve())
        assert not isinstance(writing_result, Exception)

    n5ds = N5DataSource.try_load(filesystem=filesystem, path=path)
    assert not isinstance(n5ds, Exception), str(n5ds)
    assert n5ds.retrieve() == data

def test_writing_to_precomputed_chunks():
    tmp_path = create_tmp_dir(prefix="test_writing_to_precomputed_chunks")
    datasource = ArrayDataSource(data=data, tile_shape=Shape5D(x=10, y=10))
    filesystem = OsFs.create()
    assert not isinstance(filesystem, Exception)
    sink_path = tmp_path / "mytest.precomputed"

    datasink = PrecomputedChunksSink(
        filesystem=filesystem,
        path=sink_path,
        encoding=RawEncoder(),
        interval=datasource.interval,
        resolution=datasource.spatial_resolution,
        scale_key=PurePosixPath("my_test_data"),
        tile_shape=datasource.tile_shape,
        dtype=datasource.dtype,
    )
    creation_result = datasink.open()
    if isinstance(creation_result, Exception):
        raise creation_result

    for tile in datasource.roi.get_datasource_tiles():
        writing_result = creation_result.write(tile.retrieve())
        assert not isinstance(writing_result, Exception)

    precomp_datasource = datasink.to_datasource()
    reloaded_data = precomp_datasource.retrieve()
    assert reloaded_data == data


def test_writing_to_offset_precomputed_chunks():
    tmp_path = create_tmp_dir(prefix="test_writing_to_offset_precomputed_chunks")
    data_at_1000_1000 = data.translated(Point5D(x=1000, y=1000) - data.location)
    datasource = ArrayDataSource(data=data_at_1000_1000, tile_shape=Shape5D(x=10, y=10))
    sink_path = tmp_path / "mytest.precomputed"
    filesystem = OsFs.create()
    assert not isinstance(filesystem, Exception)

    print(f"\n\n will write to '{filesystem.geturl(sink_path)}' ")

    datasink = PrecomputedChunksSink(
        filesystem=filesystem,
        path=sink_path,
        dtype=datasource.dtype,
        encoding=RawEncoder(),
        interval=datasource.interval,
        resolution=datasource.spatial_resolution,
        scale_key=PurePosixPath("my_test_data"),
        tile_shape=datasource.tile_shape,
    )
    creation_result = datasink.open()
    if isinstance(creation_result, Exception):
        raise creation_result

    for tile in datasource.roi.get_datasource_tiles():
        writing_result = creation_result.write(tile.retrieve())
        assert not isinstance(writing_result, Exception)

    precomp_datasource = datasink.to_datasource()

    reloaded_data = precomp_datasource.retrieve(interval=data_at_1000_1000.interval)
    assert (reloaded_data.raw("xyz") == data.raw("xyz")).all()


if __name__ == "__main__":
    import inspect
    import sys
    for item_name, item in inspect.getmembers(sys.modules[__name__]):
        if inspect.isfunction(item) and item_name.startswith('test'):
            print(f"Running test: {item_name}")
            item()
