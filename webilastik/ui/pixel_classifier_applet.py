from typing import List, Optional

from ndstructs.datasource import DataSource

from webilastik.ui.applet  import Applet, Slot, DerivedSlot, ValueSlot, CancelledException, CONFIRMER
from webilastik.annotations.annotation import Annotation
from webilastik.features.ilp_filter import IlpFilter
from webilastik.classifiers.pixel_classifier import PixelClassifier, VigraPixelClassifier

class PixelAnnotationApplet(Applet):
    def __init__(self, datasources: Slot[List[DataSource]]):
        self.datasources = datasources
        self.annotations = ValueSlot[List[Annotation]](
            owner=self,
            refresher=self.refresh_annotations
        )
        super().__init__()

    def refresh_annotations(self, confirmer: CONFIRMER) -> Optional[List[Annotation]]:
        current_annotations = self.annotations() or []
        current_datasources = self.datasources() or []
        annotations_to_remove : List[Annotation] = []
        for a in current_annotations:
            if a.raw_data not in current_datasources:
                annotations_to_remove.append(a)
        if annotations_to_remove and confirmer(f"This will drop {len(annotations_to_remove)} annotations. Continue?"):
            raise CancelledException("User did not want to drop annotations")
        for a in annotations_to_remove:
            current_annotations.remove(a)
        return current_annotations

    def add_annotations(self, annotations: List[Annotation], confirmer: CONFIRMER) -> None:
        current_annotations = self.annotations() or []
        current_datasources = self.datasources() or []
        for a in annotations:
            if a in current_annotations:
                raise ValueError(f"Annotation {a} already exists")
                # FIXME: check overlaps?
            if not any(a.raw_data == ds for ds in current_datasources):
                raise ValueError(f"Annotation {a} references a DataSource not present in any lane")
        self.annotations.set_value(current_annotations + annotations, confirmer=confirmer)


class PixelClassificationApplet(Applet):
    def __init__(
        self,
        *,
        feature_extractors: Slot[List[IlpFilter]],
        annotations: Slot[List[Annotation]],
    ):
        self.in_feature_extractors = feature_extractors
        self.in_annotations = annotations
        self.pixel_classifier = DerivedSlot[PixelClassifier](
            owner=self,
            value_generator=self.create_pixel_classifier
        )
        super().__init__()

    def create_pixel_classifier(self, confirmer: CONFIRMER) -> Optional[PixelClassifier]:
        feature_extractors = self.in_feature_extractors()
        annotations = self.in_annotations()
        if not feature_extractors or not annotations:
            return None
        if len(annotations) > 10:
            if not confirmer("Are you sure you want to retrain the classifier? This can take a few minutes or whatever"):
                raise CancelledException("User cancelled random forest retraining")
        return  VigraPixelClassifier.train(
            annotations=annotations,
            feature_extractors=feature_extractors
        )