from abc import abstractmethod
from typing import List, Generic, Sequence, Dict, TypeVar, Type
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
import tempfile
from functools import lru_cache
import os
import h5py


import numpy as np
from vigra.learning import RandomForest as VigraRandomForest
from sklearn.ensemble import RandomForestClassifier as ScikitRandomForestClassifier

from ndstructs import Array5D, Interval5D, Point5D, Shape5D
from webilastik.features.feature_extractor import FeatureExtractor, FeatureData
from webilastik.features.feature_extractor import FeatureExtractorCollection
from webilastik.annotations import Annotation, FeatureSamples, Color
from webilastik import Project
from webilastik.operator import Operator
from ndstructs.datasource import DataRoi, DataSource
from ndstructs.utils import JsonSerializable, from_json_data, Dereferencer

try:
    import ilastik_operator_cache # type: ignore
    operator_cache = ilastik_operator_cache
except ImportError:
    operator_cache = lru_cache()

class Predictions(Array5D):
    """An array of floats from 0.0 to 1.0. The value in each channel represents
    how likely that pixel is to belong to the classification class associated with
    that channel"""
    pass


FE = TypeVar("FE", bound=FeatureExtractor, covariant=True)

class TrainingData(Generic[FE]):
    feature_extractors: Sequence[FE]
    combined_extractor: FeatureExtractor
    color_map: Dict[Color, np.uint8]
    classes: List[np.uint8]
    num_input_channels: int
    X: np.ndarray  # shape is (num_samples, num_feature_channels)
    y: np.ndarray  # shape is (num_samples, 1)

    def __init__(
        self, *, feature_extractors: Sequence[FE], annotations: Sequence[Annotation]
    ):
        assert len(annotations) > 0
        assert len(feature_extractors) > 0
        for fx in feature_extractors:
            for annot in annotations:
                fx.ensure_applicable(annot.raw_data)

        channels = {a.raw_data.shape.c for a in annotations}
        if len(channels) != 1:
            raise ValueError(f"All annotations should be on images of same number of channels: {annotations}")
        annotations = Annotation.sort(annotations)  # sort so the meaning of the channels is always predictable
        combined_extractor = FeatureExtractorCollection(feature_extractors)
        feature_samples = [a.get_feature_samples(combined_extractor) for a in annotations]

        self.num_input_channels = channels.pop()
        self.feature_extractors = feature_extractors
        self.combined_extractor = combined_extractor
        self.color_map = Color.create_color_map(annot.color for annot in annotations)
        self.classes = list(self.color_map.values())
        self.X = np.concatenate([fs.X for fs in feature_samples])
        self.y = np.concatenate(
            [fs.get_y(self.color_map[annot.color]) for fs, annot in zip(feature_samples, annotations)]
        )
        assert self.X.shape[0] == self.y.shape[0]

class PixelClassifier(Operator[DataRoi, Predictions], Generic[FE]):
    def __init__(
        self,
        *,
        feature_extractors: Sequence[FE],
        classes: List[np.uint8],
        num_input_channels: int,
        color_map: Dict[Color, np.uint8],
    ):
        self.feature_extractors = feature_extractors
        self.feature_extractor = FeatureExtractorCollection(feature_extractors)
        self.classes = classes
        self.num_classes = len(classes)
        self.num_input_channels = num_input_channels
        self.color_map = color_map

    @abstractmethod
    def _do_predict(self, roi: DataRoi) -> Predictions:
        pass

    def get_expected_roi(self, data_slice: Interval5D) -> Interval5D:
        c_start = data_slice.c[0]
        c_stop = c_start + self.num_classes
        return data_slice.updated(c=(c_start, c_stop))

    def allocate_predictions(self, data_slice: Interval5D):
        return Predictions.allocate(interval=self.get_expected_roi(data_slice), dtype=np.dtype('float32'), value=0)

    @operator_cache # type: ignore
    def compute(self, roi: DataRoi) -> Predictions:
        self.feature_extractor.ensure_applicable(roi.datasource)
        if roi.shape.c != self.num_input_channels:
            raise ValueError(f"Bad roi: {roi}. Expected roi to have shape.c={self.num_input_channels}")
        return self._do_predict(roi=roi)


class VigraPixelClassifier(PixelClassifier[FE]):
    def __init__(
        self,
        *,
        feature_extractors: Sequence[FE],
        forests: List[VigraRandomForest],
        classes: List[np.uint8],
        num_input_channels: int,
        color_map: Dict[Color, np.uint8],
    ):
        super().__init__(
            classes=classes, feature_extractors=feature_extractors, num_input_channels=num_input_channels, color_map=color_map
        )
        self.forests = forests
        self.num_trees = sum(f.treeCount() for f in forests)

    def get_expected_dtype(self, input_dtype: np.dtype) -> np.dtype:
        return np.dtype("float32")

    @classmethod
    def train(
        cls,
        feature_extractors: Sequence[FE],
        annotations: Sequence[Annotation],
        *,
        num_trees: int = 100,
        num_forests: int = multiprocessing.cpu_count(),
        random_seed: int = 0,
    ) -> "VigraPixelClassifier[FE]":
        training_data = TrainingData[FE](feature_extractors=feature_extractors, annotations=annotations)

        def train_forest(forest_index: int) -> VigraRandomForest:
            ntrees = (num_trees // num_forests) + (forest_index < num_trees % num_forests)
            forest = VigraRandomForest(ntrees)
            forest.learnRF(training_data.X, training_data.y, random_seed)
            return forest

        with ThreadPoolExecutor(max_workers=num_forests) as executor:
            forests = list(executor.map(train_forest, range(num_forests)))

        return cls(
            feature_extractors=feature_extractors,
            forests=forests,
            num_input_channels=training_data.num_input_channels,
            classes=training_data.classes,
            color_map=training_data.color_map,
        )

    def _do_predict(self, roi: DataRoi) -> Predictions:
        feature_data = self.feature_extractor.compute(roi)
        predictions = self.allocate_predictions(roi)
        assert predictions.interval == self.get_expected_roi(roi)
        raw_linear_predictions: np.ndarray = predictions.linear_raw()

        def do_predict(forest: VigraRandomForest):
            return forest.predictProbabilities(feature_data.linear_raw()) * forest.treeCount()

        with ThreadPoolExecutor(max_workers=len(self.forests), thread_name_prefix="predictor") as executor:
            for forest_predictions in executor.map(do_predict, self.forests):
                raw_linear_predictions += forest_predictions

        raw_linear_predictions /= self.num_trees
        predictions.setflags(write=False)

        return predictions

    def get_forest_data(self):
        tmp_file_handle, tmp_file_path = tempfile.mkstemp(suffix=".h5")
        os.close(tmp_file_handle)
        for forest_index, forest in enumerate(self.forests):
            forest.writeHDF5(tmp_file_path, f"/Forest{forest_index:04d}")
        with h5py.File(tmp_file_path, "r") as f:
            out = Project.h5_group_to_dict(f["/"])
        os.remove(tmp_file_path)
        return out

    @lru_cache() #FIMXE: double check classifier __hash__/__eq__
    def __getstate__(self):
        out = self.__dict__.copy()
        forest_data = self.get_forest_data()
        out["forests"] = self.get_forest_data()
        return out

    def __setstate__(self, data):
        forests: List[VigraRandomForest] = []
        tmp_file_handle, tmp_file_path = tempfile.mkstemp(suffix=".h5")
        os.close(tmp_file_handle)
        with h5py.File(tmp_file_path, "r+") as f:
            for forest_key, forest_data in data["forests"].items():
                forest_group = f.create_group(forest_key)
                Project.populate_h5_group(forest_group, forest_data)
                forests.append(VigraRandomForest(tmp_file_path, forest_group.name))
        os.remove(tmp_file_path)

        self.__init__(
            feature_extractors=data["feature_extractors"],
            forests=forests,
            num_input_channels=data["num_input_channels"],
            classes=data["classes"],
            color_map=data["color_map"],
        )
