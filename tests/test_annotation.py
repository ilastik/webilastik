from ndstructs.point5D import Point5D
from webilastik.annotations import Annotation
from tests import get_sample_c_cells_datasource, run_all_tests
from webilastik.annotations.annotation import Color

import numpy as np

def test_collision_clearing():
    raw_data = get_sample_c_cells_datasource()
    a1 = Annotation.interpolate_from_points(
        voxels=[Point5D(x=10, y=5), Point5D(x=15, y=5)],
        raw_data=raw_data,
    )
    # a1.show(color=Color(r=np.uint8(255)))
    a2 = Annotation.interpolate_from_points(
        voxels=[Point5D(x=12, y=2), Point5D(x=12, y=7)],
        raw_data=raw_data,
    )
    original_points = set(a2.to_points())
    # a2.show(color=Color(g=np.uint8(255)))

    a2.clear_collision(a1)
    assert original_points.difference(set(a2.to_points())) == set([Point5D(x=12, y=5)])
    # a2.show(color=Color(g=np.uint8(255)))



if __name__ == "__main__":
    import sys
    run_all_tests(sys.modules[__name__])