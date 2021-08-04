from pathlib import Path
from webilastik.scheduling.hashing_executor import HashingExecutor
# from webilastik.scheduling.multiprocess_runner import MultiprocessRunner
from ndstructs.point5D import Shape5D

import numpy as np
from fs.osfs import OSFS

from ndstructs import Point5D
from webilastik.datasource import DataRoi
from webilastik.datasource import SkimageDataSource

from webilastik.annotations import Annotation, Color
from webilastik.features.channelwise_fastfilters import GaussianSmoothing, HessianOfGaussianEigenvalues
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.brushing_applet import BrushingApplet
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet


#dummy_confirmer = lambda msg: True
def dummy_confirmer(msg: str) -> bool:
    return input(msg + ": ") == "y"

def crashing_confirmer(msg: str) -> bool:
    raise ValueError("Test failed! his was not supposed to be called!")

def test_pixel_classification_workflow():
    brushing_applet = BrushingApplet("brushing_applet")
    feature_selection_applet = FeatureSelectionApplet("feature_selection_applet", datasources=brushing_applet.datasources)
    pixel_classifier_applet = PixelClassificationApplet(
        "pixel_classifier_applet",
        feature_extractors=feature_selection_applet.feature_extractors,
        annotations=brushing_applet.annotations
    )
    # wf = PixelClassificationWorkflow(
    #     feature_selection_applet=feature_selection_applet,
    #     brushing_applet=brushing_applet,
    #     pixel_classifier_applet=pixel_classifier_applet,
    #     predictions_export_applet=predictions_export_applet
    # )

    # GUI creates a datasource somewhere...
    ds = SkimageDataSource(Path("sample_data/cropped1.png"), filesystem=OSFS("."), tile_shape=Shape5D(x=400, y=400))

    # GUI creates some feature extractors
    feature_selection_applet.feature_extractors.set_value(
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
                color=Color(r=np.uint8(0), g=np.uint8(0), b=np.uint8(255)),
                raw_data=ds
            ),
            Annotation.interpolate_from_points(
                voxels=[Point5D.zero(x=238, y=101), Point5D.zero(x=229, y=139)],
                color=Color(r=np.uint8(0), g=np.uint8(0), b=np.uint8(255)),
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
    brushing_applet.annotations.set_value(brush_strokes, confirmer=dummy_confirmer)


    # preds = predictions_export_applet.compute(DataRoi(ds))

    classifier = pixel_classifier_applet.pixel_classifier()
    executor = HashingExecutor(num_workers=8)

    # calculate predictions on an arbitrary data
    preds = executor.submit(classifier.compute, ds.roi)
    preds.result().as_uint8().show_channels()

    # for png_bytes in preds.to_z_slice_pngs():
    #     path = f"/tmp/junk_test_image_{uuid.uuid4()}.png"
    #     with open(path, "wb") as outfile:
    #         outfile.write(png_bytes.getbuffer())
    #     os.system(f"gimp {path}")


    # calculate predictions on just a piece of arbitrary data
    exported_tile = executor.submit(classifier.compute, DataRoi(datasource=ds, x=(100, 200), y=(100, 200)))
    exported_tile.result().show_channels()

    # wf.save_as(Path("/tmp/blas.ilp"))

    #try removing a brush stroke
    brushing_applet.annotations.set_value(brush_strokes[1:], confirmer=dummy_confirmer)
    assert tuple(brushing_applet.annotations()) == tuple(brush_strokes[1:])
