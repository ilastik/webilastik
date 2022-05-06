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
    def __init__(self, arr: "ndarray[Any, dtype[float32]]", axiskeys: str, channel_colors: Sequence[Color], location: Point5D = Point5D.zero()):
        super().__init__(arr, axiskeys, location=location)
        self.channel_colors = tuple(channel_colors)

    def rebuild(self: "Predictions", arr: "ndarray[Any, dtype[float32]]", *, axiskeys: str, location: Optional[Point5D] = None) -> "Predictions":
        a5d = Array5D(arr=arr, axiskeys=axiskeys, location=location or self.location)
        channel_colors: Sequence[Color];
        if a5d.shape.c == self.shape.c:
            channel_colors = self.channel_colors
        elif self.interval.contains(a5d.interval):
            channel_colors = [self.channel_colors[c] for c in range(*a5d.interval.c)]
        else:
            raise RuntimeError(
                f"Don't know how to propagate prediction channel colors {self.channel_colors} when rebuilding as {a5d}"
            )
        return Predictions(arr=arr, axiskeys=axiskeys, location=location or self.location, channel_colors=channel_colors)

    def to_z_slice_pngs(self) -> Iterator[io.BytesIO]:
        for z_slice in self.split(self.shape.updated(z=1)):
            print(f"\nz_slice: {z_slice}")
            rendered_rgb = Array5D.allocate(z_slice.shape.updated(c=3), dtype=np.dtype("float32"), value=0)
            rendered_rgb_yxc = rendered_rgb.raw("yxc")

            for prediction_channel, color in zip(z_slice.split(z_slice.shape.updated(c=1)), self.channel_colors):
                print(f"\nprediction_channel: {prediction_channel}")

                class_rgb = Array5D(np.ones(prediction_channel.shape.updated(c=3).to_tuple("yxc")), axiskeys="yxc")
                class_rgb.raw("yxc")[...] *= np.asarray([color.r, color.g, color.b]) * (color.a / 255)
                class_rgb.raw("cyx")[...] *= prediction_channel.raw("yx")

                rendered_rgb_yxc += class_rgb.raw("yxc")

            out_image = PIL.Image.fromarray(rendered_rgb.raw("yxc").astype(np.uint8)) # type: ignore
            out_file = io.BytesIO()
            out_image.save(out_file, "png")
            _ = out_file.seek(0)
            yield out_file


FE = TypeVar("FE", bound=FeatureExtractor, covariant=True)

@typing.final
class TrainingData(Generic[FE]):
    feature_extractors: Sequence[FE]
    combined_extractor: FeatureExtractor
    color_map: Dict[Color, np.uint8]
    classes: List[np.uint8]
    num_input_channels: int
    X: "ndarray[Any, Any]"  # shape is (num_samples, num_feature_channels) #FIXME: add dtype hint
    y: "ndarray[Any, Any]"  # shape is (num_samples, 1) #FIXME: add dtype hint

    def __init__(
        self, *, feature_extractors: Sequence[FE], annotations: Sequence[Annotation]
    ):
        assert len(annotations) > 0, "Cannot train classifier with 0 annotations"
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

def _train_forest(random_seed: int, num_trees: int, training_data: TrainingData[FE]) -> VigraForestH5Bytes:
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
        classes: List[np.uint8],
        num_input_channels: int,
        color_map: Dict[Color, np.uint8],
    ):
        super().__init__(
            classes=classes, feature_extractors=feature_extractors, num_input_channels=num_input_channels, color_map=color_map
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
        annotations: Sequence[Annotation],
        *,
        num_trees: int = 100,
        num_forests: int = 8,
        random_seed: int = 0,
    ) -> "VigraPixelClassifier[FE]":
        training_data = TrainingData[FE](feature_extractors=feature_extractors, annotations=annotations)
        random_seeds = range(random_seed, random_seed + num_forests)
        trees_per_forest = ((num_trees // num_forests) + (forest_index < num_trees % num_forests) for forest_index in range(num_forests))

        with ProcessPoolExecutor(max_workers=num_trees) as executor:
            # we're taking the bytes instead of the forest itself because vigra forests are not picklable
            forests_bytes: Sequence[VigraForestH5Bytes] = list(executor.map(
                partial(_train_forest, training_data=training_data),
                random_seeds,
                trees_per_forest
            ))

        return cls(
            feature_extractors=feature_extractors,
            forest_h5_bytes=forests_bytes,
            num_input_channels=training_data.num_input_channels,
            classes=training_data.classes,
            color_map=training_data.color_map,
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
            channel_colors=Color.sort(self.color_map.keys()),
        )

    def __getstate__(self):
        return {
            "feature_extractors": self.feature_extractors,
            "num_input_channels": self.num_input_channels,
            "classes": self.classes,
            "color_map": self.color_map,
            "forest_h5_bytes": self.forest_h5_bytes,
        }

    def __setstate__(self, data):
        self.__init__(
            feature_extractors=data["feature_extractors"],
            forest_h5_bytes=data["forest_h5_bytes"],
            num_input_channels=data["num_input_channels"],
            classes=data["classes"],
            color_map=data["color_map"],
        )