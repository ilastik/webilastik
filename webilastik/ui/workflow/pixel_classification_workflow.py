from typing import Optional

from ndstructs.datasource import DataSource
from ndstructs.utils import JsonSerializable, Dereferencer

from webilastik.ui.applet.data_selection_applet import DataSelectionApplet, ILane, url_to_datasource
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet
from webilastik.ui.applet.brushing_applet import BrushingApplet
from webilastik.ui.applet.export_applet import ExportApplet


class PixelClassificationLane(ILane, JsonSerializable):
    def __init__(self, raw_data: DataSource, prediction_mask: Optional[DataSource]=None):
        self.raw_data = raw_data
        self.prediction_mask = prediction_mask

    def get_raw_data(self) -> DataSource:
        return self.raw_data

    @classmethod
    def from_json_data(cls, data: dict, dereferencer: Optional[Dereferencer] = None) -> "PixelClassificationLane":
        return cls(
            raw_data=url_to_datasource(data['raw_data']),
            prediction_mask=None
        )

class PixelClassificationWorkflow:
    def __init__(self):
        self.data_selection_applet = DataSelectionApplet[PixelClassificationLane]()
        self.feature_selection_applet = FeatureSelectionApplet(lanes=self.data_selection_applet.items)
        self.brushing_applet = BrushingApplet(lanes=self.data_selection_applet.items)
        self.pixel_classifier_applet = PixelClassificationApplet(
            feature_extractors=self.feature_selection_applet.items,
            annotations=self.brushing_applet.items
        )
        self.predictions_export_applet = ExportApplet(
            lanes=self.data_selection_applet.items,
            producer=self.pixel_classifier_applet.pixel_classifier
        )