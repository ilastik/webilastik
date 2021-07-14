from typing import Any, Mapping, Optional, Sequence, Type
from dataclasses import dataclass
import io
from pathlib import Path

from ndstructs.datasource import DataSource
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString

from webilastik import Project
from webilastik.ui.applet.data_selection_applet import DataSelectionApplet, ILane
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet
from webilastik.ui.applet.brushing_applet import BrushingApplet
from webilastik.classifiers.pixel_classifier import PixelClassifier
from webilastik.features.ilp_filter import IlpFilter
from webilastik.datasource import datasource_from_url


class PixelClassificationLane(ILane):
    def __init__(self, raw_data: DataSource, prediction_mask: Optional[DataSource]=None):
        self.raw_data = raw_data
        self.prediction_mask = prediction_mask

    def get_raw_data(self) -> DataSource:
        return self.raw_data

    @classmethod
    def from_json_data(cls, data: JsonValue) -> "PixelClassificationLane":
        data_dict = ensureJsonObject(data)
        raw_data_obj = ensureJsonObject(data_dict.get("raw_data"))
        raw_data_url : str = ensureJsonString(raw_data_obj.get("url"))

        mask_obj = data_dict.get("prediction_mask")
        mask_url: Optional[str] = None if mask_obj is None else ensureJsonString(ensureJsonObject(mask_obj).get("url"))

        return cls(
            raw_data=datasource_from_url(raw_data_url),
            prediction_mask=None if mask_url is None else datasource_from_url(mask_url)
        )

    def to_json_data(self) -> JsonObject:
        return {
            "raw_data": self.raw_data.to_json_data(),
            "prediction_mask": None if self.prediction_mask == None else self.prediction_mask.to_json_data()
        }

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
    # data_selection_applet: DataSelectionApplet[PixelClassificationLane]
    feature_selection_applet: FeatureSelectionApplet
    brushing_applet: BrushingApplet
    pixel_classifier_applet: PixelClassificationApplet

    @property
    def ilp_data(self) -> Mapping[str, Any]:
        return {
            "Input Data": b"FIXME!!!!", #self.data_selection_applet.get_ilp_data(PixelClassificationLane),
            "FeatureSelections": self.feature_selection_applet.ilp_data,
            "PixelClassification": self.pixel_classifier_applet.ilp_data,
            "Prediction Export": {
                "OutputFilenameFormat": "{dataset_dir}/{nickname}_{result_type}",
                "OutputFormat": "hdf5",
                "OutputInternalPath": "exported_data",
                "StorageVersion": "0.1",
            },
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
