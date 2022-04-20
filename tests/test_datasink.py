from ndstructs.point5D import Interval5D
from webilastik.filesystem.osfs import OsFs
from pathlib import PurePosixPath

import pytest
import numpy as np
from ndstructs import Point5D, Array5D, Shape5D

from webilastik.datasink.n5_dataset_sink import N5DatasetSink
from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksScaleSink
from webilastik.datasource import DataRoi, DataSource
from webilastik.datasource.array_datasource import ArrayDataSource
from webilastik.datasource.n5_datasource import N5DataSource
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksScale, RawEncoder
from webilastik.datasource.n5_attributes import GzipCompressor, N5DatasetAttributes, RawCompressor
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource, PrecomputedChunksInfo



@pytest.fixture
def data() -> Array5D:
    array = Array5D(np.arange(20 * 10 * 7).reshape(20, 10, 7), axiskeys="xyz")
    array.setflags(write=False)
    return array

@pytest.fixture
def datasource(data: Array5D) -> DataSource:
    return ArrayDataSource(data=data, tile_shape=Shape5D(x=10, y=10))

def test_n5_attributes():
    attributes = N5DatasetAttributes(
        dimensions=Shape5D(x=100, y=200),
        blockSize=Shape5D(x=10, y=20),
        axiskeys="yx",
        dataType=np.dtype("uint16").newbyteorder(">"), #type: ignore
        compression=GzipCompressor(level=3)
    )

    reserialized_attributes = N5DatasetAttributes.from_json_data(attributes.to_json_data())
    assert reserialized_attributes == attributes
    assert attributes.to_json_data()["axes"] == ("x", "y")

def test_n5_datasink(tmp_path: PurePosixPath, data: Array5D, datasource: DataSource):
    sink = N5DatasetSink(
        filesystem=OsFs(tmp_path.as_posix()),
        outer_path=PurePosixPath("test_n5_datasink.n5"),
        inner_path=PurePosixPath("/data"),
        attributes=N5DatasetAttributes(
            dimensions=datasource.shape,
            blockSize=Shape5D(x=10, y=10),
            axiskeys=data.axiskeys, #FIXME: double check this
            dataType=datasource.dtype,
            compression=RawCompressor(),
            location=Point5D.zero(x=7, y=13)
        )
    )
    sink_writer = sink.create()
    assert not isinstance(sink_writer, Exception)
    for tile in DataRoi(datasource).split(sink.tile_shape):
        sink_writer.write(tile.retrieve().translated(Point5D.zero(x=7, y=13)))

    n5ds = N5DataSource(filesystem=sink.filesystem, path=sink.full_path)
    saved_data = n5ds.retrieve()
    assert saved_data.location == Point5D.zero(x=7, y=13)
    assert saved_data == data

def test_distributed_n5_datasink(tmp_path: PurePosixPath, data: Array5D, datasource: DataSource):
    filesystem = OsFs(tmp_path.as_posix())
    outer_path = PurePosixPath("test_distributed_n5_datasink.n5")
    inner_path = PurePosixPath("/data")
    full_path = PurePosixPath("test_distributed_n5_datasink.n5/data")
    attributes = N5DatasetAttributes(
        dimensions=datasource.shape,
        blockSize=datasource.tile_shape,
        axiskeys=data.axiskeys, #FIXME: double check this
        dataType=datasource.dtype,
        compression=RawCompressor()
    )
    sink = N5DatasetSink(outer_path=outer_path, inner_path=inner_path, filesystem=filesystem, attributes=attributes)
    sink_writer = sink.create()
    assert not isinstance(sink_writer, Exception)
    sink_writers = [sink_writer] * 4

    for idx, piece in enumerate(DataRoi(datasource).default_split()):
        sink = sink_writers[idx % len(sink_writers)]
        sink.write(piece.retrieve())

    n5ds = N5DataSource(filesystem=filesystem, path=full_path)
    assert n5ds.retrieve() == data

def test_writing_to_precomputed_chunks(tmp_path: PurePosixPath, data: Array5D):
    datasource = ArrayDataSource(data=data, tile_shape=Shape5D(x=10, y=10))
    scale = PrecomputedChunksScale.from_datasource(datasource=datasource, key=PurePosixPath("my_test_data"), encoding=RawEncoder())
    sink_path = PurePosixPath("mytest.precomputed")
    filesystem = OsFs(tmp_path.as_posix())

    datasink = PrecomputedChunksScaleSink(
        filesystem=filesystem,
        info_dir=sink_path,
        scale=scale,
        dtype=datasource.dtype,
        num_channels=datasource.shape.c,
    )
    creation_result = datasink.create()
    if isinstance(creation_result, Exception):
        raise creation_result

    for tile in datasource.roi.get_datasource_tiles():
        datasink.write(tile.retrieve())

    precomp_datasource = PrecomputedChunksDataSource(path=sink_path, filesystem=filesystem, resolution=scale.resolution)
    reloaded_data = precomp_datasource.retrieve()
    assert reloaded_data == data


def test_writing_to_offset_precomputed_chunks(tmp_path: PurePosixPath, data: Array5D):
    data_at_1000_1000 = data.translated(Point5D(x=1000, y=1000) - data.location)
    datasource = ArrayDataSource(data=data_at_1000_1000, tile_shape=Shape5D(x=10, y=10))
    scale = PrecomputedChunksScale.from_datasource(datasource=datasource, key=PurePosixPath("my_test_data"), encoding=RawEncoder())
    sink_path = PurePosixPath("mytest.precomputed")
    filesystem = OsFs(tmp_path.as_posix())

    print(f"\n\n will write to '{filesystem.geturl(sink_path.as_posix())}' ")

    datasink = PrecomputedChunksScaleSink(
        filesystem=filesystem,
        info_dir=sink_path,
        scale=scale,
        num_channels=datasource.shape.c,
        dtype=datasource.dtype,
    )
    creation_result = datasink.create()
    if isinstance(creation_result, Exception):
        raise creation_result

    for tile in datasource.roi.get_datasource_tiles():
        datasink.write(tile.retrieve())

    precomp_datasource = PrecomputedChunksDataSource(path=sink_path, filesystem=filesystem, resolution=scale.resolution)

    reloaded_data = precomp_datasource.retrieve(interval=data_at_1000_1000.interval)
    assert (reloaded_data.raw("xyz") == data.raw("xyz")).all() # type: ignore
