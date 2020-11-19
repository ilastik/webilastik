from pathlib import Path
from webilastik.ui.applet import CancelledException
from webilastik.annotations import annotation

import pytest
import numpy as np
from ndstructs import Point5D
from ndstructs.datasource import DataSource, DataSourceSlice

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
    ds = DataSource.create(Path("sample_data/cropped1.png"))

    wf.data_selection_applet.add(
        [PixelClassificationLane(raw_data=ds)],
        confirmer=dummy_confirmer
    )

    # GUI creates some feature extractors
    wf.feature_selection_applet.add(
        [
            GaussianSmoothing.from_ilp_scale(scale=0.3, axis_2d="z"),
            HessianOfGaussianEigenvalues.from_ilp_scale(scale=0.7, axis_2d="z"),
        ],
        confirmer=dummy_confirmer
    )

    # GUI creates some annotations
    wf.brushing_applet.add(
        [
            Annotation.interpolate_from_points(
                voxels=[Point5D.zero(x=140, y=150), Point5D.zero(x=145, y=155)],
                color=Color(r=np.uint8(0), g=np.uint8(255), b=np.uint8(0)),
                raw_data=ds
            ),
            Annotation.interpolate_from_points(
                voxels=[Point5D.zero(x=238, y=101), Point5D.zero(x=229, y=139)],
                color=Color(r=np.uint8(0), g=np.uint8(255), b=np.uint8(0)),
                raw_data=ds
            ),
            Annotation.interpolate_from_points(
                voxels=[Point5D.zero(x=283, y=87), Point5D.zero(x=288, y=92)],
                color=Color(r=np.uint8(255), g=np.uint8(0), b=np.uint8(0)),
                raw_data=ds
            ),
            Annotation.interpolate_from_points(
                voxels=[Point5D.zero(x=274, y=168), Point5D.zero(x=256, y=191)],
                color=Color(r=np.uint8(255), g=np.uint8(0), b=np.uint8(0)),
                raw_data=ds
            ),
        ],
        confirmer=dummy_confirmer
    )

    preds = wf.predictions_export_applet.compute(DataSourceSlice(ds))
    preds.show_channels()

    # GUI clicks "export button"
    wf.predictions_export_applet.export_all()

    #check that removing a lane would drop the annotations:
    with pytest.raises(CancelledException):
        wf.data_selection_applet.remove_at(0, confirmer=lambda msg: False)

    wf.data_selection_applet.remove_at(0, confirmer=lambda msg: True)
    assert wf.brushing_applet.items() == []