# pyright: strict

import math
from pathlib import PurePosixPath
from typing import Any, Tuple, Mapping


from ndstructs.array5D import Array5D
from ndstructs.point5D import Interval5D, Point5D
from skimage.transform import resize_local_mean # pyright: ignore [reportMissingTypeStubs, reportUnknownVariableType]

from webilastik.datasink.deep_zoom_sink import DziLevelSink
from webilastik.datasource.deep_zoom_datasource import DziImageElement, DziLevelDataSource
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.datasource.deep_zoom_image import DziSizeElement
from webilastik.filesystem import IFilesystem
from webilastik.filesystem.http_fs import HttpFs
from webilastik.filesystem.os_fs import OsFs
from webilastik.utility import get_now_string


def get_sample_fs_and_path() -> Tuple[IFilesystem, PurePosixPath]:
    return(
        HttpFs(
            protocol="https",
            hostname="openseadragon.github.io",
            path=PurePosixPath("/")
        ),
        PurePosixPath("/example-images/duomo/duomo.dzi"),
    )

def get_sample_dzi_image() -> DziImageElement:
    fs, path = get_sample_fs_and_path()
    dzi_image = DziImageElement.try_load(filesystem=fs, path=path)
    assert not isinstance(dzi_image, Exception)
    return dzi_image

def get_sample_source_pyramid() -> Mapping[int, DziLevelDataSource]:
    fs, path = get_sample_fs_and_path()
    source_pyramid = DziLevelDataSource.try_load_as_pyramid(filesystem=fs, dzi_path=path)
    assert not isinstance(source_pyramid, (Exception, type(None)))
    return source_pyramid


def test_datasource():
    source = get_sample_source_pyramid()[11]
    print(f"Allocating enough space to store {source.shape}")
    sink = Array5D.allocate(interval=source.shape.to_interval5d(), axiskeys="tzyxc", dtype=source.dtype)

    for tile in source.roi.default_split():
        print(f" -->> retrieving tile at {tile.start}  ({tile.shape})")
        sink.set(tile.retrieve())

    print(f"Shape of the sink is {sink.shape}")
    # sink.show_images()

def download_entire_thing():
    osfs = OsFs.create(); assert not isinstance(osfs, Exception)
    xml_path = PurePosixPath(f"/tmp/{get_now_string()}/my_dzi/bla.dzi")
    print(f"DZI is at {xml_path}")

    dzi_image = get_sample_dzi_image()
    source_pyramid = get_sample_source_pyramid()

    sink_pyramid = DziLevelSink.create_pyramid(
        dzi_image=dzi_image,
        filesystem=osfs,
        xml_path=xml_path,
        num_channels=1,
    )
    assert not isinstance(sink_pyramid, Exception)
    assert osfs.exists(xml_path)

    for level_index in range(len(source_pyramid)):
        sink = sink_pyramid[level_index]
        source = source_pyramid[level_index]
        assert sink.shape == source.shape
        writer = sink.open()
        assert not isinstance(writer, Exception)

        for tile in source.roi.default_split():
            print(f" -->> level {level_index}: retrieving tile at {tile.start}  ({tile.shape})")
            writing_result = writer.write(tile.retrieve())
            assert not isinstance(writing_result, Exception)



def convert_to_deep_zoom():
    osfs = OsFs.create(); assert not isinstance(osfs, Exception)

    source = PrecomputedChunksDataSource.try_load(
        filesystem=osfs,
        path=PurePosixPath("/home/builder/source/webilastik/public/images/c_cells_2.precomputed"),
        spatial_resolution=(1,1,1),
    )
    assert source and not isinstance(source, Exception)

    dzi_image = DziImageElement(
        Format="png",
        Overlap=0,
        TileSize=source.tile_shape.x,
        Size=DziSizeElement(Width=source.shape.x, Height=source.shape.y)
    )

    xml_path = PurePosixPath(f"/tmp/{get_now_string()}/{source.url.path.name}/{source.url.path.name}.dzi")
    print(f"DZI is at {xml_path}")


    num_channels = source.shape.c
    assert num_channels in (1,3)

    sink_pyramid = DziLevelSink.create_pyramid(
        dzi_image=dzi_image,
        filesystem=osfs,
        xml_path=xml_path,
        num_channels=num_channels,
    )
    assert not isinstance(sink_pyramid, Exception)
    assert osfs.exists(xml_path)

    source_data = source.retrieve(source.interval)
    for sink_index in reversed(range(len(sink_pyramid))):
        sink = sink_pyramid[sink_index]
        shrunk_data_raw: Any = resize_local_mean(
            image=source_data.raw("yxc"),
            channel_axis=2,
            output_shape=sink.shape.to_tuple("yx"),
        )
        shrunk_data = Array5D(shrunk_data_raw, axiskeys="yxc").as_uint8()
        # import pydevd; pydevd.settrace()

        writer = sink.open()
        assert not isinstance(writer, Exception)
        for data_tile in shrunk_data.split(shape=sink.tile_shape):
            print(f"Writing tile {data_tile} for sink {sink_index}")
            writing_result = writer.write(data_tile)
            assert not isinstance(writing_result, Exception)


def convert_to_deep_zoom_lazily():
    osfs = OsFs.create(); assert not isinstance(osfs, Exception)

    source = PrecomputedChunksDataSource.try_load(
        filesystem=osfs,
        path=PurePosixPath("/home/builder/source/webilastik/public/images/c_cells_2.precomputed"),
        # path=PurePosixPath("/home/builder/Downloads/openseadragon/tiled_images/church_dzi/church.dzie"),
        spatial_resolution=(1,1,1),
    )
    assert source and not isinstance(source, Exception)

    dzi_image = DziImageElement(
        Format="png",
        Overlap=0,
        TileSize=source.tile_shape.x,
        Size=DziSizeElement(Width=source.shape.x, Height=source.shape.y)
    )

    xml_path = PurePosixPath(f"/tmp/{get_now_string()}/{source.url.path.name}/{source.url.path.name}.dzi")
    print(f"DZI is at {xml_path}")


    num_channels = source.shape.c
    assert num_channels in (1,3)

    sink_pyramid = DziLevelSink.create_pyramid(
        dzi_image=dzi_image,
        filesystem=osfs,
        xml_path=xml_path,
        num_channels=num_channels,
    )
    assert not isinstance(sink_pyramid, Exception)
    assert osfs.exists(xml_path)

    for sink_index in reversed(range(len(sink_pyramid))):
        print(f"Processing level {sink_index}")
        sink = sink_pyramid[sink_index]
        writer = sink.open()
        assert not isinstance(writer, Exception)
        ratio_x = source.shape.x / sink.shape.x
        ratio_y = source.shape.y / sink.shape.y
        ratio_z = source.shape.z / sink.shape.z

        print(f"{ratio_x=} {ratio_y=}")

        for sink_tile in sink.interval.split(sink.tile_shape):
            sink_roi_plus_halo = sink_tile.enlarged(radius=Point5D(x=1, y=1)).clamped(sink.interval)

            source_interval_plus_halo = Interval5D.zero(
                x=(
                    math.floor(sink_roi_plus_halo.start.x * ratio_x),
                    math.ceil(sink_roi_plus_halo.stop.x * ratio_x)
                ),
                y=(
                    math.floor(sink_roi_plus_halo.start.y * ratio_y),
                    math.ceil(sink_roi_plus_halo.stop.y * ratio_y)
                ),
                z=(
                    math.floor(sink_roi_plus_halo.start.z * ratio_z),
                    math.ceil(sink_roi_plus_halo.stop.z * ratio_z)
                ),
                c=source.interval.c,
            ).clamped(source.interval)

            source_data_with_halo = source.retrieve(source_interval_plus_halo)

            sink_tile_data_with_halo_raw: Any = resize_local_mean(
                image=source_data_with_halo.raw("zyxc"),
                channel_axis=3,
                output_shape=sink_roi_plus_halo.shape.to_tuple("zyx"),
            )

            sink_tile_data_with_halo = Array5D(sink_tile_data_with_halo_raw, axiskeys="zyxc", location=sink_roi_plus_halo.start).as_uint8()
            sink_tile_data = sink_tile_data_with_halo.cut(sink_tile)

            writing_result = writer.write(sink_tile_data)
            assert not isinstance(writing_result, Exception)


        level_sources = DziLevelDataSource.try_load_as_pyramid(filesystem=osfs, dzi_path=xml_path)
        assert level_sources and not isinstance(level_sources, Exception)

        # _ = level_sources[sink_index].retrieve().show_images()








# download_entire_thing()
convert_to_deep_zoom_lazily()

