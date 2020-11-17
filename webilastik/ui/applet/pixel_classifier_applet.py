from typing import List, Optional, Sequence, Dict

from ndstructs.datasource import DataSource, DataSourceSlice
import numpy as np

from webilastik.ui.applet  import Applet, SequenceProviderApplet, Slot, CancelledException, CONFIRMER
from webilastik.ui.applet.data_selection_applet import ILane
from webilastik.annotations.annotation import Annotation, Color
from webilastik.features.ilp_filter import IlpFilter
from webilastik.classifiers.pixel_classifier import Predictions
from webilastik.classifiers.ilp_pixel_classifier import IlpVigraPixelClassifier

class PixelClassificationApplet(Applet):
    pixel_classifier: Slot[IlpVigraPixelClassifier]

    def __init__(
        self,
        *,
        feature_extractors: Slot[Sequence[IlpFilter]],
        annotations: Slot[Sequence[Annotation]],
    ):
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
        feature_extractors = self._in_feature_extractors()
        annotations = self._in_annotations()
        if not feature_extractors or not annotations:
            return None
        if len(annotations) > 10:
            if not confirmer("Are you sure you want to retrain the classifier? This can take a few minutes or whatever"):
                raise CancelledException("User cancelled random forest retraining")
        print("Retraining pixel classifier..................")
        return  IlpVigraPixelClassifier.train(
            annotations=annotations,
            feature_extractors=feature_extractors
        )

    def _create_color_map(self, confirmer: CONFIRMER) -> Optional[Dict[Color, np.uint8]]:
        annotations = self._in_annotations()
        if annotations is None:
            return None
        return Color.create_color_map([a.color for a in annotations])

    def predict(self, roi: DataSourceSlice) -> Predictions:
        classifier = self.pixel_classifier()
        if classifier is None:
            raise ValueError("Applet has no classifier")
        return classifier.compute(roi)