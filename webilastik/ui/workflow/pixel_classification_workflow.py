from dataclasses import dataclass

from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet
from webilastik.ui.applet.brushing_applet import BrushingApplet


@dataclass
class PixelClassificationWorkflow:
    feature_selection_applet: FeatureSelectionApplet
    brushing_applet: BrushingApplet
    pixel_classifier_applet: PixelClassificationApplet
