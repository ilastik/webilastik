from typing import List

from webilastik.ui.applet  import Applet, Slot, DerivedSlot, ValueSlot, CancelledException, CONFIRMER
from webilastik.annotations.annotation import Annotation
from webilastik.features.ilp_filter import IlpFilter
from webilastik.classifiers.pixel_classifier import VigraPixelClassifier

class FeatureSelectionApplet(Applet):
    def __init__(self):
        self.feature_extractors = ValueSlot[List[IlpFilter]](owner=self)
        super().__init__(borrowed_slots=[], owned_slots=[self.feature_extractors])

    def clear_feature_extractors(self, *, confirmer: CONFIRMER = noop_confirmer) -> None:
        self.feature_extractors.set_value(None, confirmer=confirmer)

    def add_feature_extractors(self, value: List[IlpFilter], confirmer: CONFIRMER = noop_confirmer):
        current_extractors = self.feature_extractors()
        for extractor in value:
            if extractor in current_extractors:
                raise ValueError(f"Feature Extractor {extractor} is already present in this Workflow")
        self.feature_extractors.set_value(current_extractors + value, confirmer=confirmer)


class PixelAnnotationApplet(Applet):
    def __init__(self):
        self.annotations = ValueSlot[List[Annotation]](owner=self)
        super().__init__(borrowed_slots=[], owned_slots=[self.annotations])


class PixelClassificationApplet(Applet):
    def __init__(
        self,
        *,
        feature_extractors_inslot: Slot[List[IlpFilter]],
        annotations_inslot: Slot[List[Annotation]],
    ):
        self.feature_extractors_inslot = feature_extractors_inslot
        self.annotations_inslot = annotations_inslot
        self.pixel_classifier = DerivedSlot[PixelClassifier](
            owner=self,
            value_generator=self.create_pixel_classifier
        )
        super().__init__(
            borrowed_slots=[feature_extractors_inslot, annotations_inslot],
            owned_slots=[self.pixel_classifier]
        )

    def create_pixel_classifier(self, confirmer: CONFIRMER) -> Optional[PixelClassifier]:
        feature_extractors = self.feature_extractors_inslot()
        annotations = self.annotations_inslot()
        if not feature_extractors or not annotations:
            return None
        if len(annotations) > 10:
            if not confirmer("Are you sure you want to retrain the classifier? This can take a few minutes or whatever"):
                raise CancelledException("User cancelled random forest retraining")
        return  VigraPixelClassifier.train(
            annotations=annotations,
            feature_extractors=feature_extractors
        )