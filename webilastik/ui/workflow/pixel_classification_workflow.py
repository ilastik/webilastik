from ndstructs.datasource import DataSource

from webilastik.ui.applet.data_selection_applet import DataSelectionApplet
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.pixel_classifier_applet import PixelAnnotationApplet, PixelClassificationApplet
from webilastik.ui.applet.export_applet import ExportApplet

class PixelClassificationWorkflow:
    def __init__(self):
        self.data_selection_applet = DataSelectionApplet()
        self.feature_selection_applet = FeatureSelectionApplet(datasources=self.data_selection_applet.datasources)
        self.annotations_applet = PixelAnnotationApplet(datasources=self.data_selection_applet.datasources)
        self.pixel_classifier_applet = PixelClassificationApplet(
            feature_extractors=self.feature_selection_applet.feature_extractors,
            annotations=self.annotations_applet.annotations
        )
        self.predictions_export_applet = ExportApplet(
            datasources=self.data_selection_applet.datasources,
            producer=self.pixel_classifier_applet.pixel_classifier
        )