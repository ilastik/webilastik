from typing import List, Optional, Sequence

from ndstructs.datasource import DataSource

from webilastik.ui.applet  import Applet, SequenceProviderApplet, Slot, CancelledException, CONFIRMER
from webilastik.ui.applet.data_selection_applet import ILane
from webilastik.annotations.annotation import Annotation
from webilastik.features.ilp_filter import IlpFilter
from webilastik.classifiers.pixel_classifier import PixelClassifier, VigraPixelClassifier

class PixelClassificationApplet(Applet):
    pixel_classifier: Slot[PixelClassifier]

    def __init__(
        self,
        *,
        feature_extractors: Slot[Sequence[IlpFilter]],
        annotations: Slot[Sequence[Annotation]],
    ):
        self._in_feature_extractors = feature_extractors
        self._in_annotations = annotations
        self.pixel_classifier = Slot[PixelClassifier](
            owner=self,
            refresher=self._create_pixel_classifier
        )
        super().__init__()

    def _create_pixel_classifier(self, confirmer: CONFIRMER) -> Optional[PixelClassifier]:
        feature_extractors = self._in_feature_extractors()
        annotations = self._in_annotations()
        if not feature_extractors or not annotations:
            return None
        if len(annotations) > 10:
            if not confirmer("Are you sure you want to retrain the classifier? This can take a few minutes or whatever"):
                raise CancelledException("User cancelled random forest retraining")
        return  VigraPixelClassifier.train(
            annotations=annotations,
            feature_extractors=feature_extractors
        )