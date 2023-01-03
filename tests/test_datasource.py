#!/usr/bin/env python

from typing import Optional, Any, Tuple
import tempfile
from pathlib import PurePosixPath
import pickle

import numpy as np
import h5py
import json
import skimage.io # type: ignore
from ndstructs.point5D import Shape5D, Interval5D, Point5D
from ndstructs.array5D import Array5D

from webilastik.datasource import DataRoi
from webilastik.datasink.n5_dataset_sink import N5DataSink
from webilastik.datasource.n5_datasource import N5DataSource
from webilastik.datasource.n5_attributes import N5Compressor, RawCompressor
from webilastik.datasource import DataSource
from webilastik.datasource.array_datasource import ArrayDataSource
from webilastik.datasource.skimage_datasource import SkimageDataSource
from webilastik.filesystem import IFilesystem
from webilastik.filesystem.os_fs import OsFs

# fmt: off
raw = np.asarray([
    [1,  2,  3,  4,  5],
    [6,  7,  8,  9,  10],
    [11, 12, 13, 14, 15],
    [16, 17, 18, 19, 20],
]).astype(np.uint8)

raw_0_2x0_2y = np.asarray([
    [1,2],
    [6,7]
])

raw_0_2x2_4y = np.asarray([
    [11,12],
    [16,17]
])

raw_2_4x0_2y = np.asarray([
    [3,4],
    [8,9]
])

raw_2_4x2_4y = expected_raw = np.asarray([
    [13,14],
    [18,19]
])

raw_4_5x0_2y = np.asarray([
    [5],
    [10]
])

raw_4_5x2_4y = np.asarray([
    [15],
    [20]
])
# fmt: on


def create_png(array: Array5D) -> PurePosixPath:
    png_path = tempfile.mkstemp()[1] + ".png"
    skimage.io.imsave(png_path, array.raw("yxc"))
    return PurePosixPath(png_path)


def create_n5(
    array: Array5D, *, axiskeys: Optional[str] = None, chunk_size: Shape5D, compression: N5Compressor = RawCompressor()
) -> Tuple[IFilesystem, PurePosixPath]:
    path = PurePosixPath(tempfile.mkstemp()[1] + ".n5/data")
    fs = OsFs.create()
    assert not isinstance(fs, Exception)
    sink = N5DataSink(
        path=path,
        filesystem=fs,
        tile_shape=chunk_size,
        c_axiskeys=axiskeys or array.axiskeys,
        compressor=compression,
        dtype=array.dtype,
        interval=array.interval,
    )
    sink_writer = sink.open()
    assert not isinstance(sink_writer, Exception)

    for tile in array.split(chunk_size):
        sink_writer.write(tile)
    return (fs, path)


def create_h5(array: Array5D, axiskeys_style: str, chunk_shape: Optional[Shape5D] = None, axiskeys: str = "xyztc"):
    raw_chunk_shape = (chunk_shape or Shape5D() * 2).clamped(maximum=array.shape).to_tuple(axiskeys)

    path = tempfile.mkstemp()[1] + ".h5"
    f = h5py.File(path, "w")
    ds = f.create_dataset("data", chunks=raw_chunk_shape, data=array.raw(axiskeys))
    if axiskeys_style == "dims":
        for key, dim in zip(axiskeys, ds.dims):
            dim.label = key
    elif axiskeys_style == "vigra":
        type_flags = {"x": 2, "y": 2, "z": 2, "t": 2, "c": 1}
        axistags = [{"key": key, "typeflags": type_flags[key], "resolution": 0, "description": ""} for key in axiskeys]
        ds.attrs["axistags"] = json.dumps({"axes": axistags})
    else:
        raise Exception(f"Bad axiskeys_style: {axiskeys_style}")

    return PurePosixPath(path)


png_image: PurePosixPath = create_png(Array5D(raw, axiskeys="yx"))

def tile_equals(tile: DataSource, axiskeys: str, raw: "np.ndarray[Any, Any]") -> bool:
    return (tile.retrieve().raw(axiskeys) == raw).all()


def test_retrieve_roi_smaller_than_tile():
    # fmt: off
    data = Array5D(np.asarray([
        [[   1,    2,    3,    4,     5],
         [   6,    7,    8,    9,    10],
         [  11,   12,   13,   14,    15],
         [  16,   17,   18,   19,    20]],

        [[ 100,  200,  300,  400,   500],
         [ 600,  700,  800,  900,  1000],
         [1100, 1200, 1300, 1400,  1500],
         [1600, 1700, 1800, 1900,  2000]],
    ]).astype(np.uint32), axiskeys="cyx")

    expected_cyx = np.asarray([
        [[ 100,  200,  300,  400],
         [ 600,  700,  800,  900],
         [1100, 1200, 1300, 1400],
         [1600, 1700, 1800, 1900]]
    ])
    # fmt: on
    fs, path = create_n5(data, chunk_size=Shape5D(c=2, y=4, x=4))
    assert not isinstance(fs, Exception)
    ds = N5DataSource.try_load(path=path, filesystem=fs)
    assert not isinstance(ds, Exception)
    smaller_than_tile = ds.retrieve(c=1, y=(0, 4), x=(0, 4))
    assert np.all(smaller_than_tile.raw("cyx") == expected_cyx)


def test_n5_datasource():
    # fmt: off
    data = Array5D(np.asarray([
        [1,  2,  3,  4,  5 ],
        [6,  7,  8,  9,  10],
        [11, 12, 13, 14, 15],
        [16, 17, 18, 19, 20]
    ]).astype(np.uint8), axiskeys="yx")
    # fmt: on

    fs, path = create_n5(data, chunk_size=Shape5D(x=2, y=2))
    assert not isinstance(fs, Exception)
    ds = N5DataSource.try_load(path=path, filesystem=fs)
    assert not isinstance(ds, Exception), str(ds)
    assert ds.shape == data.shape

    # fmt: off
    expected_raw_piece = Array5D(np.asarray([
        [1, 2, 3],
        [6, 7, 8]
    ]).astype(np.uint8), axiskeys="yx")
    # fmt: on
    assert ds.retrieve(x=(0, 3), y=(0, 2)) == expected_raw_piece

    ds2 = pickle.loads(pickle.dumps(ds))
    assert ds2.retrieve(x=(0, 3), y=(0, 2)) == expected_raw_piece

# def test_h5_datasource():
#     data_2d = Array5D(np.arange(100).reshape(10, 10), axiskeys="yx")
#     h5_path = create_h5(data_2d, axiskeys_style="vigra", chunk_shape=Shape5D(x=3, y=3))
#     ds = H5DataSource(outer_path=h5_path, inner_path=PurePosixPath("/data"), filesystem=OsFs())
#     assert ds.shape == data_2d.shape
#     assert ds.tile_shape == Shape5D(x=3, y=3)

#     slc = ds.interval.updated(x=(0, 3), y=(0, 2))
#     assert (ds.retrieve(slc).raw("yx") == data_2d.cut(slc).raw("yx")).all()

#     data_3d = Array5D(np.arange(10 * 10 * 10).reshape(10, 10, 10), axiskeys="zyx")
#     h5_path = create_h5(data_3d, axiskeys_style="vigra", chunk_shape=Shape5D(x=3, y=3))
#     ds = H5DataSource(outer_path=h5_path, inner_path=PurePosixPath("/data"), filesystem=OsFs())
#     assert ds.shape == data_3d.shape
#     assert ds.tile_shape == Shape5D(x=3, y=3)

#     slc = ds.interval.updated(x=(0, 3), y=(0, 2), z=3)
#     assert (ds.retrieve(slc).raw("yxz") == data_3d.cut(slc).raw("yxz")).all()



def test_skimage_datasource_tiles():
    fs = OsFs.create()
    assert not isinstance(fs, Exception)
    bs = DataRoi(SkimageDataSource(path=png_image, filesystem=fs))
    num_checked_tiles = 0
    for tile in bs.split(Shape5D(x=2, y=2)):
        if tile == Interval5D.zero(x=(0, 2), y=(0, 2)):
            expected_raw = raw_0_2x0_2y
        elif tile == Interval5D.zero(x=(0, 2), y=(2, 4)):
            expected_raw = raw_0_2x2_4y
        elif tile == Interval5D.zero(x=(2, 4), y=(0, 2)):
            expected_raw = raw_2_4x0_2y
        elif tile == Interval5D.zero(x=(2, 4), y=(2, 4)):
            expected_raw = raw_2_4x2_4y
        elif tile == Interval5D.zero(x=(4, 5), y=(0, 2)):
            expected_raw = raw_4_5x0_2y
        elif tile == Interval5D.zero(x=(4, 5), y=(2, 4)):
            expected_raw = raw_4_5x2_4y
        else:
            raise Exception(f"Unexpected tile {tile}")
        assert (tile.retrieve().raw("yx") == expected_raw).all()
        num_checked_tiles += 1
    assert num_checked_tiles == 6


def test_neighboring_tiles():
    # fmt: off
    arr = Array5D(np.asarray([
        [10, 11, 12,   20, 21, 22,   30],
        [13, 14, 15,   23, 24, 25,   33],
        [16, 17, 18,   26, 27, 28,   36],

        [40, 41, 42,   50, 51, 52,   60],
        [43, 44, 45,   53, 54, 55,   63],
        [46, 47, 48,   56, 57, 58,   66],

        [70, 71, 72,   80, 81, 82,   90],
        [73, 74, 75,   83, 84, 85,   93],
        [76, 77, 78,   86, 87, 88,   96],

        [0,   1,  2,    3,  4,  5,    6]], dtype=np.uint8), axiskeys="yx")

    fs = OsFs.create()
    assert not isinstance(fs, Exception)
    ds = SkimageDataSource(path=create_png(arr), filesystem=fs)

    fifties_slice = DataRoi(ds, x=(3, 6), y=(3, 6))
    expected_fifties_slice = Array5D(np.asarray([
        [50, 51, 52],
        [53, 54, 55],
        [56, 57, 58]
    ]), axiskeys="yx")
    # fmt: on

    top_slice = DataRoi(ds, x=(3, 6), y=(0, 3))
    bottom_slice = DataRoi(ds, x=(3, 6), y=(6, 9))

    right_slice = DataRoi(ds, x=(6, 7), y=(3, 6))
    left_slice = DataRoi(ds, x=(0, 3), y=(3, 6))

    # fmt: off
    fifties_neighbor_data = {
        top_slice: Array5D(np.asarray([
            [20, 21, 22],
            [23, 24, 25],
            [26, 27, 28]
        ]), axiskeys="yx"),

        right_slice: Array5D(np.asarray([
            [60],
            [63],
            [66]
        ]), axiskeys="yx"),

        bottom_slice: Array5D(np.asarray([
            [80, 81, 82],
            [83, 84, 85],
            [86, 87, 88]
        ]), axiskeys="yx"),

        left_slice: Array5D(np.asarray([
            [40, 41, 42],
            [43, 44, 45],
            [46, 47, 48]
        ]), axiskeys="yx"),
    }

    # fmt: on

    assert (fifties_slice.retrieve().raw("yx") == expected_fifties_slice.raw("yx")).all()

    for neighbor in fifties_slice.get_neighboring_tiles(tile_shape=Shape5D(x=3, y=3)):
        try:
            expected_slice = fifties_neighbor_data.pop(neighbor)
            assert (expected_slice.raw("yx") == neighbor.retrieve().raw("yx")).all()
        except KeyError:
            print(f"\nWas searching for ", neighbor, "\n")
            for k in fifties_neighbor_data.keys():
                print("--->>> ", k)
    assert len(fifties_neighbor_data) == 0


# def test_sequence_datasource():
#     # fmt: off
#     img1_data = Array5D(np.asarray([
#        [[100, 101, 102, 103, 104],
#         [105, 106, 107, 108, 109],
#         [110, 111, 112, 113, 114],
#         [115, 116, 117, 118, 119]],

#        [[120, 121, 122, 123, 124],
#         [125, 126, 127, 128, 129],
#         [130, 131, 132, 133, 134],
#         [135, 136, 137, 138, 139]],

#        [[140, 141, 142, 143, 144],
#         [145, 146, 147, 148, 149],
#         [150, 151, 152, 153, 154],
#         [155, 156, 157, 158, 159]]
#     ]), axiskeys="cyx")

#     img2_data = Array5D(np.asarray([
#        [[200, 201, 202, 203, 204],
#         [205, 206, 207, 208, 209],
#         [210, 211, 212, 213, 214],
#         [215, 216, 217, 218, 219]],

#        [[220, 221, 222, 223, 224],
#         [225, 226, 227, 228, 229],
#         [230, 231, 232, 233, 234],
#         [235, 236, 237, 238, 239]],

#        [[240, 241, 242, 243, 244],
#         [245, 246, 247, 248, 249],
#         [250, 251, 252, 253, 254],
#         [255, 256, 257, 258, 259]]
#     ]), axiskeys="cyx")

#     img3_data = Array5D(np.asarray([
#        [[300, 301, 302, 303, 304],
#         [305, 306, 307, 308, 309],
#         [310, 311, 312, 313, 314],
#         [315, 316, 317, 318, 319]],

#        [[320, 321, 322, 323, 324],
#         [325, 326, 327, 328, 329],
#         [330, 331, 332, 333, 334],
#         [335, 336, 337, 338, 339]],

#        [[340, 341, 342, 343, 344],
#         [345, 346, 347, 348, 349],
#         [350, 351, 352, 353, 354],
#         [355, 356, 357, 358, 359]]
#     ]), axiskeys="cyx")

#     expected_x_2_4__y_1_3 = Array5D(np.asarray([
#       [[[107, 108],
#         [112, 113]],

#        [[127, 128],
#         [132, 133]],

#        [[147, 148],
#         [152, 153]]],


#       [[[207, 208],
#         [212, 213]],

#        [[227, 228],
#         [232, 233]],

#        [[247, 248],
#         [252, 253]]],


#       [[[307, 308],
#         [312, 313]],

#        [[327, 328],
#         [332, 333]],

#        [[347, 348],
#         [352, 353]]],
#     ]), axiskeys="zcyx")
#     # fmt: on
#     slice_x_2_4__y_1_3 = {"x": (2, 4), "y": (1, 3)}

#     h5_outer_paths = [
#         # create_n5(img1_data, axiskeys="cyx"),
#         create_h5(img1_data, axiskeys_style="dims", axiskeys="cyx"),
#         # create_n5(img2_data, axiskeys="cyx"),
#         create_h5(img2_data, axiskeys_style="dims", axiskeys="cyx"),
#         # create_n5(img3_data, axiskeys="cyx"),
#         create_h5(img3_data, axiskeys_style="dims", axiskeys="cyx"),
#     ]

#     def stack_h5s(stack_axis: str) -> List[H5DataSource]:
#         offset = Point5D.zero()
#         stack: List[H5DataSource] = []
#         for outer_path in h5_outer_paths:
#             stack.append(H5DataSource(outer_path=outer_path, inner_path=PurePosixPath("/data"), filesystem=OsFs(), location=offset))
#             offset += Point5D.zero(**{stack_axis: stack[-1].shape[stack_axis]})
#         return stack

#     seq_ds = SequenceDataSource(datasources=stack_h5s("z"), stack_axis="z")
#     assert seq_ds.shape == Shape5D(x=5, y=4, c=3, z=3)
#     data = seq_ds.retrieve(**slice_x_2_4__y_1_3)
#     assert (expected_x_2_4__y_1_3.raw("xyzc") == data.raw("xyzc")).all()

#     seq_ds = SequenceDataSource(datasources=stack_h5s("z"), stack_axis="z")
#     data = seq_ds.retrieve(**slice_x_2_4__y_1_3)
#     assert (expected_x_2_4__y_1_3.raw("xyzc") == data.raw("xyzc")).all()


# def test_relabeling_datasource():
#    data = Array5D(np.arange(200).astype(np.uint8).reshape(20, 10), axiskeys="xy")
#
#    png_path = create_png(data)
#    n5_path = create_n5(data)
#    h5_path = create_h5(data, axiskeys_style="dims")
#
#    adjusted = DataSource.create(png_path, axiskeys="zy")
#    assert adjusted.shape == Shape5D(z=data.shape.y, y=data.shape.x)
#
#    data_slc = Interval5D(y=(4, 7), x=(3, 5))
#    adjusted_slice = Interval5D(z=data_slc.y, y=data_slc.x)
#
#    assert (data.cut(data_slc).raw("yx") == adjusted.retrieve(adjusted_slice).raw("zy")).all()


def test_data_roi_get_tiles_can_clamp_to_datasource_tiles():
    # fmt: off
    data = Array5D(np.asarray([
        [1,  2,  3,  4,  5],
        [6,  7,  8,  9,  10],
        [11, 12, 13, 14, 15],
        [16, 17, 18, 19, 20],
    ]).astype(np.uint8), axiskeys="yx")
    # fmt: on

    ds = ArrayDataSource(data=data, tile_shape=Shape5D(x=2, y=2))
    data_slice = DataRoi(datasource=ds, x=(1, 4), y=(0, 3))

    # fmt: off
    dataslice_expected_data = Array5D(np.asarray([
        [2,  3,  4],
        [7,  8,  9],
        [12, 13, 14]
    ]).astype(np.uint8), axiskeys="yx", location=Point5D.zero(x=1))
    # fmt: on

    assert data_slice.retrieve() == dataslice_expected_data

    # fmt: off
    dataslice_expected_slices = [
        Array5D(np.asarray([
            [1, 2],
            [6, 7]
        ]).astype(np.uint8), axiskeys="yx", location=Point5D.zero()),

        Array5D(np.asarray([
            [3,  4],
            [8,  9],
        ]).astype(np.uint8), axiskeys="yx", location=Point5D.zero(x=2)),

        Array5D(np.asarray([
            [11, 12],
            [16, 17],
        ]).astype(np.uint8), axiskeys="yx", location=Point5D.zero(y=2)),

        Array5D(np.asarray([
            [13, 14],
            [18, 19],
        ]).astype(np.uint8), axiskeys="yx", location=Point5D.zero(x=2, y=2))
    ]
    # fmt: on
    expected_slice_dict = {a.interval: a for a in dataslice_expected_slices}
    for piece in data_slice.get_datasource_tiles(clamp_to_datasource=True):
        expected_data = expected_slice_dict.pop(piece.interval)
        assert expected_data == piece.retrieve()
    assert len(expected_slice_dict) == 0

if __name__ == "__main__":
    import inspect
    import sys
    for item_name, item in inspect.getmembers(sys.modules[__name__]):
        if inspect.isfunction(item) and item_name.startswith('test'):
            print(f"Running test: {item_name}")
            item()