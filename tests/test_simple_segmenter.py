from ndstructs.array5D import Array5D
import numpy as np
from webilastik.datasource.array_datasource import ArrayDataSource

from webilastik.simple_segmenter import SimpleSegmenter


def test_simple_segmenter():
    input_data = ArrayDataSource(
        data=Array5D(np.asarray([
           [[ 0.1,  0.1,   0.0,  1.0],
            [ 0.2,  0.2,   0.0,  0.0],
            [ 0.3,  0.3,   0.1,  0.2],
            [ 0.4,  0.4,   0.0,  0.0]],

           [[ 0.4,  0.4,   0.0,  0.0],
            [ 0.3,  0.3,   0.0,  0.0],
            [ 0.2,  0.2,   0.4,  0.0],
            [ 0.1,  0.1,   0.0,  0.0]]
        ]), axiskeys="cyx"),
    )

    expected_segmentation = [
        Array5D(np.asarray([
           [[  0,   0, 255, 255],
            [  0,   0, 255, 255],
            [255, 255,   0, 255],
            [255, 255, 255, 255]],

           [[  0,   0,   0,   0],
            [  0,   0,   0,   0],
            [  0,   0,   0,   0],
            [  0,   0,   0,   0]],

           [[  0,   0,   0,   0],
            [  0,   0,   0,   0],
            [  0,   0,   0,   0],
            [  0,   0,   0,   0]],
        ]), axiskeys="cyx"),

        Array5D(np.asarray([
           [[255, 255,   0,   0],
            [255, 255,   0,   0],
            [  0,   0, 255,   0],
            [  0,   0,   0,   0]],

           [[  0,   0,   0,   0],
            [  0,   0,   0,   0],
            [  0,   0,   0,   0],
            [  0,   0,   0,   0]],

           [[  0,   0,   0,   0],
            [  0,   0,   0,   0],
            [  0,   0,   0,   0],
            [  0,   0,   0,   0]],
        ]), axiskeys="cyx")
    ]

    segmentations = [SimpleSegmenter(channel_index=i)(input_data.roi) for i in range(input_data.shape.c)]
    for seg, expected_seg in zip(segmentations, expected_segmentation):
        assert np.all(seg.raw("cyx") == expected_seg.raw("cyx"))

if __name__ == "__main__":
    test_simple_segmenter()