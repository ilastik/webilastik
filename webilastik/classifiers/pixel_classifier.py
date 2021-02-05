from abc import abstractmethod
import functools
from typing import List, Tuple, Iterable, Optional, Sequence, Dict, TypeVar, Type
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from threading import Lock

import numpy as np
import vigra
from vigra.learning import RandomForest as VigraRandomForest
from sklearn.ensemble import RandomForestClassifier as ScikitRandomForestClassifier

from ndstructs import Array5D, Interval5D, Point5D, Shape5D
from webilastik.features.feature_extractor import FeatureExtractor, FeatureData, ChannelwiseFilter
from webilastik.features.feature_extractor import FeatureExtractorCollection
from webilastik.annotations import Annotation, FeatureSamples, Color
from webilastik.operator import Operator
from ndstructs.datasource import DataRoi, DataSource
from ndstructs.utils import JsonSerializable, from_json_data, Dereferencer


class Predictions(Array5D):
    """An array of floats from 0.0 to 1.0. The value in each channel represents
    how likely that pixel is to belong to the classification class associated with
    that channel"""
    pass

class TrainingData:
    feature_extractors: Sequence[FeatureExtractor]
    combined_extractor: FeatureExtractor
    color_map: Dict[Color, np.uint8]
    classes: List[np.uint8]
    num_input_channels: int
    X: np.ndarray  # shape is (num_samples, num_feature_channels)
    y: np.ndarray  # shape is (num_samples, 1)

    def __init__(
        self, *, feature_extractors: Sequence[FeatureExtractor], annotations: Sequence[Annotation]
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


class PixelClassifier(Operator, JsonSerializable):
    def __init__(
        self,
        *,
        feature_extractors: Sequence[FeatureExtractor],
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

    def get_expected_roi(self, data_slice: Interval5D) -> Interval5D:
        c_start = data_slice.c[0]
        c_stop = c_start + self.num_classes
        return data_slice.updated(c=(c_start, c_stop))

    def allocate_predictions(self, data_slice: Interval5D):
        return Predictions.allocate(interval=self.get_expected_roi(data_slice), dtype=np.dtype('float32'))

    def predict(self, roi: DataRoi, out: Predictions = None) -> Predictions:
        self.feature_extractor.ensure_applicable(roi.datasource)
        if roi.shape.c != self.num_input_channels:
            raise ValueError(f"Bad roi: {roi}. Expected roi to have shape.c={self.num_input_channels}")
        return self._do_predict(roi=roi, out=out)

    @abstractmethod
    def _do_predict(self, roi: DataRoi, out: Predictions = None) -> Predictions:
        pass

    @functools.lru_cache()
    def compute(self, roi: DataRoi) -> Array5D:
        return self.predict(roi)


class ScikitLearnPixelClassifier(PixelClassifier):
    def __init__(
        self,
        *,
        feature_extractors: Sequence[FeatureExtractor],
        forest: ScikitRandomForestClassifier,
        classes: List[np.uint8],
        num_input_channels: int,
        color_map: Dict[Color, np.uint8],
    ):
        super().__init__(classes=classes, feature_extractors=feature_extractors, num_input_channels=num_input_channels, color_map=color_map)
        self.forest = forest

    @classmethod
    def train(
        cls,
        feature_extractors: Sequence[FeatureExtractor],
        annotations: Tuple[Annotation],
        *,
        num_trees: int = 100,
        random_seed: int = 0,
    ) -> "ScikitLearnPixelClassifier":
        training_data = TrainingData(feature_extractors=feature_extractors, annotations=annotations)
        forest = ScikitRandomForestClassifier(n_estimators=num_trees, random_state=random_seed)
        forest.fit(training_data.X, training_data.y.squeeze())
        num_channels = {a.raw_data for a in annotations}
        return cls(
            forest=forest,
            feature_extractors=feature_extractors,
            classes=training_data.classes,
            num_input_channels=training_data.num_input_channels,
            color_map=training_data.color_map,
        )

    def get_expected_dtype(self, input_dtype: np.dtype) -> np.dtype:
        return np.dtype("float32")

    @classmethod
    def from_json_data(cls, data: dict, dereferencer: Optional[Dereferencer] = None) -> "ScikitLearnPixelClassifier":
        return from_json_data(cls.train, data, dereferencer=dereferencer)

    def _do_predict(self, roi: DataRoi, out: Optional[Predictions] = None) -> Predictions:
        feature_data = self.feature_extractor.compute(roi)
        predictions_shape = roi.shape.updated(c=self.num_classes)
        predictions_raw_line = self.forest.predict_proba(feature_data.linear_raw())
        predictions = Predictions.from_line(predictions_raw_line, shape=predictions_shape, location=roi.start)
        if out is not None:
            assert out.shape == predictions.shape
            out.localSet(predictions)
            return out
        else:
            return predictions


VIGRA_CLASSIFIER = TypeVar("VIGRA_CLASSIFIER", bound="VigraPixelClassifier", covariant=True)
class VigraPixelClassifier(PixelClassifier):
    def __init__(
        self,
        *,
        feature_extractors: Sequence[FeatureExtractor],
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
        cls: Type[VIGRA_CLASSIFIER],
        feature_extractors: Sequence[FeatureExtractor],
        annotations: Sequence[Annotation],
        *,
        num_trees: int = 100,
        num_forests: int = multiprocessing.cpu_count(),
        random_seed: int = 0,
    ) -> VIGRA_CLASSIFIER:
        training_data = TrainingData(feature_extractors=feature_extractors, annotations=annotations)

        tree_counts = np.array([num_trees // num_forests] * num_forests)
        tree_counts[: num_trees % num_forests] += 1
        tree_counts = list(map(int, tree_counts))

        def train_forest(forest_index: int) -> VigraRandomForest:
            forest = VigraRandomForest(tree_counts[forest_index])
            forest.learnRF(training_data.X, training_data.y, random_seed)
            return forest

        # executor = ThreadPoolExecutor(max_workers=num_forests)
        # forests = list(executor.map(train_forest, range(num_forests)))
        forests = list(map(train_forest, range(num_forests)))
        # executor.shutdown()
        return cls(
            feature_extractors=feature_extractors,
            forests=forests,
            num_input_channels=training_data.num_input_channels,
            classes=training_data.classes,
            color_map=training_data.color_map,
        )

    @classmethod
    def from_json_data(cls, data: dict, dereferencer: Optional[Dereferencer] = None) -> "VigraPixelClassifier":
        return from_json_data(cls.train, data)

    def _do_predict(self, roi: DataRoi, out: Predictions = None) -> Predictions:
        feature_data = self.feature_extractor.compute(roi)
        predictions = out or self.allocate_predictions(roi)
        assert predictions.interval == self.get_expected_roi(roi)
        raw_linear_predictions = predictions.linear_raw()
        raw_linear_predictions[...] = 0
        lock = Lock()

        def do_predict(forest):
            nonlocal raw_linear_predictions
            forest_predictions = forest.predictProbabilities(feature_data.linear_raw())
            forest_predictions *= forest.treeCount()
            with lock:
                raw_linear_predictions += forest_predictions

        # executor = ThreadPoolExecutor(max_workers=len(self.forests), thread_name_prefix="predictor")
        list(map(do_predict, self.forests))
        # list(executor.map(do_predict, self.forests))
        # executor.shutdown()

        raw_linear_predictions /= self.num_trees

        return predictions
