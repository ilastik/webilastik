from ndstructs.array5D import Array5D
import numpy as np
from webilastik.datasource import ArrayDataSource

from webilastik.simple_segmenter import SimpleSegmenter


def test_simple_segmenter():
    segmenter = SimpleSegmenter()

    input_data = ArrayDataSource.from_array5d(
        Array5D(np.asarray([
           [[ 0.1,  0.1,   0.0,  1.0],
            [ 0.2,  0.2,   0.0,  0.0],
            [ 0.3,  0.3,   0.1,  0.2],
            [ 0.4,  0.4,   0.0,  0.0]],

           [[ 0.4,  0.4,   0.0,  0.0],
            [ 0.3,  0.3,   0.0,  0.0],
            [ 0.2,  0.2,   0.4,  0.0],
            [ 0.1,  0.1,   0.0,  0.0]]
        ]), axiskeys="cyx")
    )

    expected_segmentation = Array5D(np.asarray([
        [[  0,   0, 255, 255],
         [  0,   0, 255, 255],
         [255, 255,   0, 255],
         [255, 255, 255, 255]],

        [[255, 255,   0,   0],
         [255, 255,   0,   0],
         [  0,   0, 255,   0],
         [  0,   0,   0,   0]],
    ]), axiskeys="cyx")

    segmentation = segmenter.compute(input_data.roi).raw("cyx")
    assert np.all(segmentation == expected_segmentation.raw("cyx"))