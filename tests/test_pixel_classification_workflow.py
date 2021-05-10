from pathlib import Path
from ndstructs.point5D import Shape5D

import pytest
import numpy as np
from fs.osfs import OSFS

from ndstructs import Point5D
from ndstructs.datasource import DataSource, DataRoi
from ndstructs.datasource.DataSource import SkimageDataSource

from webilastik.ui.applet import CancelledException
from webilastik.annotations import Annotation, Color
from webilastik.features.channelwise_fastfilters import GaussianSmoothing, HessianOfGaussianEigenvalues
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationLane, PixelClassificationWorkflow
from webilastik.ui.workflow.pixel_classification_workflow_gui import PixelClassificationWorkflowGui
from webilastik.ui.applet.data_selection_applet import DataSelectionApplet
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.brushing_applet import BrushingApplet
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet
from webilastik.ui.applet.export_applet import ExportApplet


#dummy_confirmer = lambda msg: True
def dummy_confirmer(msg: str) -> bool:
    return input(msg + ": ") == "y"

def crashing_confirmer(msg: str) -> bool:
    raise ValueError("Test failed! his was not supposed to be called!")

def test_pixel_classification_workflow():
    data_selection_applet = DataSelectionApplet[PixelClassificationLane]("data_selection_applet")
    feature_selection_applet = FeatureSelectionApplet("feature_selection_applet", lanes=data_selection_applet.lanes)
    brushing_applet = BrushingApplet("brushing_applet", lanes=data_selection_applet.lanes)
    pixel_classifier_applet = PixelClassificationApplet(
        "pixel_classifier_applet",
        lanes=data_selection_applet.lanes,
        feature_extractors=feature_selection_applet.feature_extractors,
        annotations=brushing_applet.annotations
    )
    predictions_export_applet = ExportApplet(
        "predictions_export_applet",
        lanes=data_selection_applet.lanes,
        producer=pixel_classifier_applet.pixel_classifier
    )
    wf = PixelClassificationWorkflow(
        data_selection_applet=data_selection_applet,
        feature_selection_applet=feature_selection_applet,
        brushing_applet=brushing_applet,
        pixel_classifier_applet=pixel_classifier_applet,
        predictions_export_applet=predictions_export_applet
    )

    # GUI creates a datasource somewhere...
    ds = SkimageDataSource(Path("sample_data/cropped1.png"), filesystem=OSFS("."), tile_shape=Shape5D(x=400, y=400))

    wf.data_selection_applet.lanes.set_value(
        [PixelClassificationLane(raw_data=ds)],
        confirmer=dummy_confirmer
    )

    # GUI creates some feature extractors
    wf.feature_selection_applet.feature_extractors.set_value(
        [
            GaussianSmoothing.from_ilp_scale(scale=0.3, axis_2d="z"),
            HessianOfGaussianEigenvalues.from_ilp_scale(scale=0.7, axis_2d="z"),
        ],
        confirmer=dummy_confirmer
    )

    # GUI creates some annotations
    brush_strokes = [
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
    ]
    wf.brushing_applet.annotations.set_value(brush_strokes, confirmer=dummy_confirmer)


    # calculate predictions on an arbitrary data
    preds = wf.predictions_export_applet.compute(DataRoi(ds))
    # preds.as_uint8().show_channels()

    # calculate predictions on just a piece of arbitrary data
    exported_tile = wf.predictions_export_applet.compute(DataRoi(datasource=ds, x=(100, 200), y=(100, 200)))
    # exported_tile.show_channels()

    # GUI clicks "export button"
    wf.predictions_export_applet.export_all()

    wf.save_as(Path("/tmp/blas.ilp"))

    #try removing a brush stroke
    wf.brushing_applet.annotations.set_value(brush_strokes[1:], confirmer=dummy_confirmer)
    assert tuple(wf.brushing_applet.annotations()) == tuple(brush_strokes[1:])

    #check that removing a lane would drop the annotations:
    with pytest.raises(CancelledException):
        wf.data_selection_applet.lanes.set_value(None, confirmer=lambda msg: False)

    wf.data_selection_applet.lanes.set_value(None, confirmer=lambda msg: True)
    assert wf.brushing_applet.annotations.get() == None
