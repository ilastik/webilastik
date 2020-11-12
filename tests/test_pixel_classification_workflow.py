from pathlib import Path
from webilastik.ui.applet import CancelledException
from webilastik.annotations import annotation

import pytest
import numpy as np
from ndstructs import Point5D
from ndstructs.datasource import DataSource

from webilastik.annotations import Annotation, Color
from webilastik.features.channelwise_fastfilters import GaussianSmoothing, HessianOfGaussianEigenvalues
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow, PixelClassificationLane


#dummy_confirmer = lambda msg: True
def dummy_confirmer(msg: str) -> bool:
    return input(msg + ": ") == "y"

def crashing_confirmer(msg: str) -> bool:
    raise ValueError("Test failed! his was not supposed to be called!")

def test_pixel_classification_workflow():
    wf = PixelClassificationWorkflow()

    # GUI creates a datasource somewhere...
    ds = DataSource.create(Path("sample_data/2d_cells_apoptotic_1c.png"))

    wf.data_selection_applet.add(
        [PixelClassificationLane(raw_data=ds)],
        confirmer=dummy_confirmer
    )

    # GUI creates some feature extractors
    extractors = [
        GaussianSmoothing.from_ilp_scale(scale=0.3, axis_2d="z", num_input_channels=ds.shape.c),
        HessianOfGaussianEigenvalues.from_ilp_scale(scale=0.7, axis_2d="z", num_input_channels=ds.shape.c),
    ]

    wf.feature_selection_applet.add(extractors, confirmer=dummy_confirmer)

    # GUI creates some annotations
    wf.brushing_applet.add(
        [
            Annotation.interpolate_from_points(
                color=Color(r=np.uint8(255)),
                voxels=[
                    Point5D.zero(x=760, y=266),
                    Point5D.zero(x=761, y=267),
                ],
                raw_data=ds
            ),
            Annotation.interpolate_from_points(
                color=Color(r=np.uint8(255)),
                voxels=[
                    Point5D.zero(x=432, y=633),
                    Point5D.zero(x=433, y=634)
                ],
                raw_data=ds
            ),

            Annotation.interpolate_from_points(
                color=Color(g=np.uint8(255)),
                voxels=[
                    Point5D.zero(x=1028, y=325),
                    Point5D.zero(x=1029, y=326)
                ],
                raw_data=ds
            ),
            Annotation.interpolate_from_points(
                color=Color(g=np.uint8(255)),
                voxels=[
                    Point5D.zero(x=234, y=238),
                    Point5D.zero(x=235, y=239)
                ],
                raw_data=ds
            ),
        ],
        confirmer=dummy_confirmer
    )

    # GUI clicks "export button"
    wf.predictions_export_applet.export_all()

    #check that removing a lane would drop the annotations:
    with pytest.raises(CancelledException):
        wf.data_selection_applet.remove_at(0, confirmer=lambda msg: False)

    wf.data_selection_applet.remove_at(0, confirmer=lambda msg: True)
    assert wf.brushing_applet.items() == []