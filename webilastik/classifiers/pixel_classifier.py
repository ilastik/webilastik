from abc import abstractmethod
from functools import partial
import pickle
from typing import Any, Iterator, List, Generic, Optional, Sequence, Dict, TypeVar
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


class PickableVigraRandomForest:
    def __init__(self, forest: VigraRandomForest, forest_data: "Dict[str, Any] | None" = None) -> None:
        self._forest: VigraRandomForest = forest
        if forest_data:
            self._forest_data = forest_data
            return

        tmp_file_handle, tmp_file_path = tempfile.mkstemp(suffix=".h5") # FIXME
        os.close(tmp_file_handle)
        self._forest.writeHDF5(tmp_file_path, f"/Forest")
        with h5py.File(tmp_file_path, "r") as f:
            self._forest_data = read_h5_group(f["/Forest"])
        os.remove(tmp_file_path)
        super().__init__()

    def __getstate__(self) -> IlpGroup:
        return self._forest_data

    def __setstate__(self, data: Dict[str, Any]):
        tmp_file_handle, tmp_file_path = tempfile.mkstemp(suffix=".h5")
        os.close(tmp_file_handle)
        with h5py.File(tmp_file_path, "r+") as f:
            forest_group = f.create_group("Forest")
            populate_h5_group(forest_group, data)
            forest = VigraRandomForest(tmp_file_path, forest_group.name)
        os.remove(tmp_file_path)
        self.__init__(forest=forest, forest_data=data)

    def predict(self, feature_data: Array5D) -> "ndarray[Any, dtype[float32]]":
        return self._forest.predictProbabilities(feature_data.linear_raw()) * self._forest.treeCount()

    def treeCount(self) -> int:
        return self._forest.treeCount()

    def to_ilp_data(self) -> IlpGroup:
        return self._forest_data

def _train_forest(random_seed: int, num_trees: int, training_data: TrainingData[FE]) -> PickableVigraRandomForest:
    forest = VigraRandomForest(num_trees)
    # forest.learnRF(training_data.X, training_data.y, random_seed)
    forest.learnRF(training_data.X, training_data.y, 0)
    return PickableVigraRandomForest(forest=forest)

class VigraPixelClassifier(PixelClassifier[FE]):
    def __init__(
        self,
        *,
        feature_extractors: Sequence[FE],
        forests: List[PickableVigraRandomForest],
        classes: List[np.uint8],
        num_input_channels: int,
        color_map: Dict[Color, np.uint8],
    ):
        super().__init__(
            classes=classes, feature_extractors=feature_extractors, num_input_channels=num_input_channels, color_map=color_map
        )
        self.forests = forests
        self.num_trees = sum(f.treeCount() for f in forests)

    def to_ilp_forests(self) -> IlpGroup:
        return {
            f"Forest{forest_index:04}": forest.to_ilp_data() for forest_index, forest in enumerate(self.forests)
        }

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
            forests = list(executor.map(
                partial(_train_forest, training_data=training_data),
                random_seeds,
                trees_per_forest
            ))

        return cls(
            feature_extractors=feature_extractors,
            forests=forests,
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

        for forest in self.forests:
            raw_linear_predictions += forest.predict(feature_data)

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
            "forests": self.forests
        }

    def __setstate__(self, data):
        self.__init__(
            feature_extractors=data["feature_extractors"],
            forests=data["forests"],
            num_input_channels=data["num_input_channels"],
            classes=data["classes"],
            color_map=data["color_map"],
        )