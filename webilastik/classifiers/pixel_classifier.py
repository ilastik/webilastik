from abc import abstractmethod
from functools import partial
from pathlib import Path
import pickle
from typing import Any, Final, Iterator, List, Generic, NewType, Optional, Sequence, Dict, TypeVar
import tempfile
import os
import typing
import h5py
import PIL
import io
from dataclasses import dataclass


import numpy as np
from numpy import ndarray, dtype, float32
from vigra.learning import RandomForest as VigraRandomForest
from concurrent.futures import ProcessPoolExecutor

from ndstructs.array5D import Array5D
from ndstructs.point5D import Interval5D, Point5D
from webilastik.features.feature_extractor import FeatureExtractor
from webilastik.features.feature_extractor import FeatureExtractorCollection
from webilastik.annotations import Annotation, Color
from webilastik.classic_ilastik.ilp import IlpGroup, populate_h5_group, read_h5_group
from webilastik.operator import Operator
from webilastik.datasource import DataRoi, DataSource

class Predictions(Array5D):
    """An array of floats from 0.0 to 1.0. The value in each channel represents
    how likely that pixel is to belong to the classification class associated with
    that channel"""

    def to_z_slice_pngs(self, class_colors: Sequence[Color]) -> Iterator[io.BytesIO]:
        for z_slice in self.split(self.shape.updated(z=1)):
            print(f"\nz_slice: {z_slice}")
            rendered_rgb = Array5D.allocate(z_slice.shape.updated(c=3), dtype=np.dtype("float32"), value=0)
            rendered_rgb_yxc = rendered_rgb.raw("yxc")

            for prediction_channel, color in zip(z_slice.split(z_slice.shape.updated(c=1)), class_colors):
                print(f"\nprediction_channel: {prediction_channel}")

                class_rgb = Array5D(np.ones(prediction_channel.shape.updated(c=3).to_tuple("yxc")), axiskeys="yxc")
                class_rgb.raw("yxc")[...] *= np.asarray([color.r, color.g, color.b])
                class_rgb.raw("cyx")[...] *= prediction_channel.raw("yx")

                rendered_rgb_yxc += class_rgb.raw("yxc")

            out_image = PIL.Image.fromarray(rendered_rgb.raw("yxc").astype(np.uint8)) # type: ignore
            out_file = io.BytesIO()
            out_image.save(out_file, "png")
            _ = out_file.seek(0)
            yield out_file


FE = TypeVar("FE", bound=FeatureExtractor, covariant=True)

@typing.final
@dataclass
class TrainingData:
    feature_extractors: Sequence[FeatureExtractor]
    combined_extractor: FeatureExtractor
    num_input_channels: int
    num_classes: int
    X: "ndarray[Any, Any]"  # shape is (num_samples, num_feature_channels) #FIXME: add dtype hint
    y: "ndarray[Any, Any]"  # shape is (num_samples, 1) #FIXME: add dtype hint

    @classmethod
    def create(
        cls, *, feature_extractors: Sequence[FeatureExtractor], label_classes: Sequence[Sequence[Annotation]]
    ) -> "TrainingData | ValueError":
        if sum(len(labels) for labels in label_classes) == 0:
            return ValueError("Cannot train classifier with 0 annotations")
        if len(feature_extractors) == 0:
            return ValueError("Empty feature extractor sequence")

        annotated_datasources = {annotation.raw_data for labels in label_classes for annotation in labels}
        for fx in feature_extractors:
            for ds in annotated_datasources:
                if not fx.is_applicable_to(ds):
                    return ValueError(f"feature {fx} is not compatible with {ds}")
        channel_counts = {ds.shape.c for ds in annotated_datasources}
        if len(channel_counts) > 1:
            return ValueError(f"All annotations should be on images of same number of channels")

        combined_extractor = FeatureExtractorCollection(feature_extractors)

        X_parts: List["np.ndarray[Any, np.dtype[Any]]"] = []
        y_parts: List["np.ndarray[Any, np.dtype[np.uint32]]"] = []
        for label_index, labels in enumerate(label_classes, start=1):
            for annotation in labels:
                feature_sample = annotation.get_feature_samples(combined_extractor)
                X_parts.append(feature_sample.X)
                y_parts.append(
                    feature_sample.get_y(label_class=np.uint8(label_index))
                )

        feature_extractors = feature_extractors
        combined_extractor = combined_extractor
        X = np.concatenate(X_parts)
        y = np.concatenate(y_parts)
        assert X.shape[0] == y.shape[0]

        return TrainingData(
            feature_extractors=feature_extractors,
            combined_extractor=combined_extractor,
            num_input_channels=channel_counts.pop(),
            num_classes=len(label_classes),
            X=X,
            y=y,
        )

class PixelClassifier(Operator[DataRoi, Predictions], Generic[FE]):
    def __init__(
        self,
        *,
        feature_extractors: Sequence[FE],
        num_classes: int,
        num_input_channels: int,
    ):
        self.feature_extractors = feature_extractors
        self.feature_extractor = FeatureExtractorCollection(feature_extractors)
        self.num_classes = num_classes
        self.classes: Sequence[np.uint8] = [np.uint8(class_index + 1) for class_index in range(num_classes)]
        self.num_input_channels = num_input_channels
        super().__init__()

    @abstractmethod
    def _do_predict(self, roi: DataRoi) -> Predictions:
        pass

    def get_expected_roi(self, data_slice: Interval5D) -> Interval5D:
        c_start = data_slice.c[0]
        c_stop = c_start + self.num_classes
        return data_slice.updated(c=(c_start, c_stop))

    def is_applicable_to(self, datasource: DataSource) -> bool:
        return (
            self.feature_extractor.is_applicable_to(datasource) and
            datasource.roi.c == self.num_input_channels
        )

    def compute(self, roi: DataRoi) -> Predictions:
        self.feature_extractor.ensure_applicable(roi.datasource)
        if roi.shape.c != self.num_input_channels:
            raise ValueError(f"Bad roi: {roi}. Expected roi to have shape.c={self.num_input_channels}")
        return self._do_predict(roi=roi)

VigraForestH5Bytes = NewType("VigraForestH5Bytes", bytes)

def dump_to_temp_file(contents: bytes) -> Path:
    tmp_file_handle, tmp_file_path = tempfile.mkstemp(suffix=".h5") # FIXME
    num_bytes_written = os.write(tmp_file_handle, contents)
    assert num_bytes_written == len(contents)
    os.close(tmp_file_handle)
    return Path(tmp_file_path)

def vigra_forest_to_h5_bytes(forest: VigraRandomForest) -> VigraForestH5Bytes:
    tmp_file_handle, tmp_file_path = tempfile.mkstemp(suffix=".h5") # FIXME
    os.close(tmp_file_handle)
    forest.writeHDF5(tmp_file_path, f"/")
    with open(tmp_file_path, "rb") as f:
        out = VigraForestH5Bytes(f.read())
    os.remove(tmp_file_path)
    return out

def h5_bytes_to_vigra_forest(h5_bytes: VigraForestH5Bytes) -> VigraRandomForest:
    tmp_file_path = dump_to_temp_file(h5_bytes)
    out = VigraRandomForest(str(tmp_file_path), "/")
    os.remove(tmp_file_path)
    return out

def _train_forest(random_seed: int, num_trees: int, training_data: TrainingData) -> VigraForestH5Bytes:
    forest = VigraRandomForest(num_trees)
    # forest.learnRF(training_data.X, training_data.y, random_seed)
    _ = forest.learnRF(training_data.X, training_data.y, 0)
    return vigra_forest_to_h5_bytes(forest)

class VigraPixelClassifier(PixelClassifier[FE]):
    def __init__(
        self,
        *,
        feature_extractors: Sequence[FE],
        forest_h5_bytes: "Sequence[VigraForestH5Bytes]",
        num_input_channels: int,
        num_classes: int,
    ):
        super().__init__(
            num_classes=num_classes, feature_extractors=feature_extractors, num_input_channels=num_input_channels
        )
        self.forest_h5_bytes: Final[Sequence[VigraForestH5Bytes]] = forest_h5_bytes
        self.forests: Final[Sequence[VigraRandomForest]] = [h5_bytes_to_vigra_forest(forest_bytes) for forest_bytes in forest_h5_bytes]
        self.num_trees: Final[int] = sum(f.treeCount() for f in self.forests)

    def get_expected_dtype(self, input_dtype: "dtype[Any]") -> "dtype[float32]":
        return np.dtype("float32")

    @classmethod
    def train(
        cls,
        feature_extractors: Sequence[FE],
        label_classes: Sequence[Sequence[Annotation]],
        *,
        num_trees: int = 100,
        num_forests: int = 8,
        random_seed: int = 0,
    ) -> "VigraPixelClassifier[FE] | ValueError":
        training_data_result = TrainingData.create(feature_extractors=feature_extractors, label_classes=label_classes)
        if isinstance(training_data_result, Exception):
            return training_data_result
        random_seeds = range(random_seed, random_seed + num_forests)
        trees_per_forest = ((num_trees // num_forests) + (forest_index < num_trees % num_forests) for forest_index in range(num_forests))

        with ProcessPoolExecutor(max_workers=num_trees) as executor:
            # we're taking the bytes instead of the forest itself because vigra forests are not picklable
            forests_bytes: Sequence[VigraForestH5Bytes] = list(executor.map(
                partial(_train_forest, training_data=training_data_result),
                random_seeds,
                trees_per_forest
            ))

        return cls(
            feature_extractors=feature_extractors,
            forest_h5_bytes=forests_bytes,
            num_input_channels=training_data_result.num_input_channels,
            num_classes=training_data_result.num_classes,
        )


    def _do_predict(self, roi: DataRoi) -> Predictions:
        feature_data = self.feature_extractor.compute(roi)

        predictions = Array5D.allocate(
            interval=self.get_expected_roi(roi),
            dtype=np.dtype('float32'),
            value=0,
        )
        assert predictions.interval == self.get_expected_roi(roi)
        raw_linear_predictions: "ndarray[Any, dtype[float32]]" = predictions.linear_raw()

        #fixme: should this run in some sort of worker pool?
        for forest in self.forests:
            raw_linear_predictions += forest.predictProbabilities(feature_data.linear_raw()) * forest.treeCount()

        raw_linear_predictions /= self.num_trees
        predictions.setflags(write=False)

        return Predictions(
            arr=predictions.raw(predictions.axiskeys),
            axiskeys=predictions.axiskeys,
            location=predictions.location,
        )

    def __getstate__(self):
        return {
            "feature_extractors": self.feature_extractors,
            "num_input_channels": self.num_input_channels,
            "num_classes": self.num_classes,
            "forest_h5_bytes": self.forest_h5_bytes,
        }

    def __setstate__(self, data):
        self.__init__(
            feature_extractors=data["feature_extractors"],
            forest_h5_bytes=data["forest_h5_bytes"],
            num_input_channels=data["num_input_channels"],
            num_classes=data["num_classes"],
        )