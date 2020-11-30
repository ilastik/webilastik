from typing import List, Optional, Sequence, Dict, Any, Iterator
import itertools

from ndstructs.datasource import DataSource, DataSourceSlice
import numpy as np

from webilastik.ui.applet  import Applet, NotReadyException, SequenceProviderApplet, Slot, CancelledException, CONFIRMER
from webilastik.ui.applet.data_selection_applet import ILane
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.annotations.annotation import Annotation, Color
from webilastik.features.ilp_filter import IlpFilter
from webilastik.classifiers.pixel_classifier import Predictions
from webilastik.classifiers.ilp_pixel_classifier import IlpVigraPixelClassifier

class PixelClassificationApplet(Applet):
    pixel_classifier: Slot[IlpVigraPixelClassifier]

    def __init__(
        self,
        *,
        lanes: Slot[Sequence[ILane]], #this is only necessary to produce a .ilp file
        feature_extractors: Slot[Sequence[IlpFilter]],
        annotations: Slot[Sequence[Annotation]],
    ):
        self._in_lanes = lanes
        self._in_feature_extractors = feature_extractors
        self._in_annotations = annotations
        self.pixel_classifier = Slot[IlpVigraPixelClassifier](
            owner=self,
            refresher=self._create_pixel_classifier
        )
        self.color_map = Slot[Dict[Color, np.uint8]](
            owner=self,
            refresher=self._create_color_map
        )
        super().__init__()

    def _create_pixel_classifier(self, confirmer: CONFIRMER) -> Optional[IlpVigraPixelClassifier]:
        return  IlpVigraPixelClassifier.train(
            annotations=self._in_annotations(),
            feature_extractors=self._in_feature_extractors()
        )

    def _create_color_map(self, confirmer: CONFIRMER) -> Optional[Dict[Color, np.uint8]]:
        annotations = self._in_annotations.get() or []
        return Color.create_color_map([a.color for a in annotations])

    def predict(self, roi: DataSourceSlice) -> Predictions:
        classifier = self.pixel_classifier()
        return classifier.compute(roi)

    def get_ilp_classifier_feature_names(self) -> Iterator[bytes]:
        lanes = self._in_lanes()
        classifier = self.pixel_classifier()
        if lanes is None or classifier is None:
            return
        num_input_channels = lanes[0].get_raw_data().shape.c
        for fe in sorted(classifier.feature_extractors, key=lambda ex: FeatureSelectionApplet.ilp_feature_names.index(ex.__class__.__name__)):
            for c in range(num_input_channels * fe.channel_multiplier):
                name_and_channel = fe.ilp_name + f" [{c}]"
                yield name_and_channel.encode("utf8")

    def get_classifier_ilp_data(self) -> dict:
        classifier = self.pixel_classifier()
        out = classifier.get_forest_data()
        feature_names: Iterator[bytes] = self.get_ilp_classifier_feature_names()
        out["feature_names"] = np.asarray(list(feature_names))
        out[
            "pickled_type"
        ] = b"clazyflow.classifiers.parallelVigraRfLazyflowClassifier\nParallelVigraRfLazyflowClassifier\np0\n."
        out["known_labels"] = np.asarray(classifier.classes).astype(np.uint32)
        return out

    @property
    def ilp_data(self) -> Dict[str, Any]:
        out = {
            "Bookmarks": {"0000": []},
            "StorageVersion": "0.1",
            "ClassifierFactory": IlpVigraPixelClassifier.DEFAULT_ILP_CLASSIFIER_FACTORY,
        }
        try:
            out["ClassifierForests"] = self.get_classifier_ilp_data()
            out["ClassifierFactory"] = self.pixel_classifier().ilp_classifier_factory
        except NotReadyException:
            pass

        out["LabelSets"] = labelSets = {"labels000": {}}  # empty labels still produce this in classic ilastik
        color_map = self.color_map()
        for lane_idx, lane in enumerate(self._in_lanes() or []):
            lane_annotations = [annot for annot in self._in_annotations() or [] if annot.raw_data == lane.get_raw_data()]
            label_data = Annotation.dump_as_ilp_data(lane_annotations, color_map=color_map)
            labelSets[f"labels{lane_idx:03d}"] = label_data
        out["LabelColors"] = np.asarray([color.rgba[:-1] for color in color_map.keys()], dtype=np.int64)
        out["PmapColors"] = out["LabelColors"]
        out["LabelNames"] = np.asarray([color.name.encode("utf8") for color in color_map.keys()])
        return out