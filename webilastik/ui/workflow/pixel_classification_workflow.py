from typing import Any, Mapping, Optional, Sequence, Type
from dataclasses import dataclass
import io
from pathlib import Path
from webilastik.features.ilp_filter import IlpFilter

from ndstructs.datasource import DataSource
from ndstructs.utils import JsonSerializable, Dereferencer
from ndstructs.utils.JsonSerializable import JSON_ARRAY, JSON_VALUE

from webilastik import Project
from webilastik.ui.applet.data_selection_applet import DataSelectionApplet, ILane, Lane, url_to_datasource
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet
from webilastik.ui.applet.brushing_applet import BrushingApplet
from webilastik.ui.applet.export_applet import ExportApplet
from webilastik.classifiers.pixel_classifier import PixelClassifier


class PixelClassificationLane(ILane, JsonSerializable):
    def __init__(self, raw_data: DataSource, prediction_mask: Optional[DataSource]=None):
        self.raw_data = raw_data
        self.prediction_mask = prediction_mask

    def get_raw_data(self) -> DataSource:
        return self.raw_data

    @classmethod
    def from_json_data(cls, data: JSON_VALUE, dereferencer: Optional[Dereferencer] = None) -> "PixelClassificationLane":
        return cls(
            raw_data=url_to_datasource(data['raw_data']), # type: ignore
            prediction_mask=None #FIXME
        )

    @classmethod
    def get_role_names(cls) -> Sequence[str]:
        return ["Raw Data", "Prediction Mask"]

    @property
    def ilp_data(self) -> Mapping[str, Any]:
        return {
            "Raw Data": self.datasource_to_ilp_data(self.raw_data),
            "Prediction Mask": {} if self.prediction_mask is None else self.datasource_to_ilp_data(self.prediction_mask),
        }

@dataclass
class PixelClassificationWorkflow:
    data_selection_applet: DataSelectionApplet[PixelClassificationLane]
    feature_selection_applet: FeatureSelectionApplet
    brushing_applet: BrushingApplet[PixelClassificationLane]
    pixel_classifier_applet: PixelClassificationApplet[PixelClassificationLane]
    predictions_export_applet : ExportApplet[PixelClassificationLane, PixelClassifier[IlpFilter]]

    @property
    def ilp_data(self) -> Mapping[str, Any]:
        return {
            "Input Data": self.data_selection_applet.get_ilp_data(PixelClassificationLane),
            "FeatureSelections": self.feature_selection_applet.ilp_data,
            "PixelClassification": self.pixel_classifier_applet.ilp_data,
            "Prediction Export": self.predictions_export_applet.ilp_data,
            "currentApplet": 0,
            "ilastikVersion": b"1.3.2post1",  # FIXME
            "time": b"Wed Mar 11 15:40:37 2020",  # FIXME
            "workflowName": b"Pixel Classification",
        }

    @property
    def ilp_file(self) -> io.BufferedIOBase:
        project, backing_file = Project.from_ilp_data(self.ilp_data)
        project.close()
        backing_file.seek(0)
        return backing_file

    def save_as(self, path: Path):
        with open(path, 'wb') as f:
            f.write(self.ilp_file.read())
