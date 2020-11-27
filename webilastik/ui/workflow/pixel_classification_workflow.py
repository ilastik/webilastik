from typing import Optional, Sequence, Type
from dataclasses import dataclass
import io
from pathlib import Path

from ndstructs.datasource import DataSource
from ndstructs.utils import JsonSerializable, Dereferencer

from webilastik import Project
from webilastik.ui.applet.data_selection_applet import DataSelectionApplet, ILane, Lane, url_to_datasource
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
            prediction_mask=None #FIXME
        )


@dataclass
class PixelClassificationWorkflow:
    data_selection_applet: DataSelectionApplet[PixelClassificationLane]
    feature_selection_applet: FeatureSelectionApplet
    brushing_applet: BrushingApplet
    pixel_classifier_applet: PixelClassificationApplet
    predictions_export_applet : ExportApplet
