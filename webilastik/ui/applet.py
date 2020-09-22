from abc import ABC, abstractmethod
import typing
from typing import List, Optional, Callable, Any, Generic, TypeVar, Dict, Set

from webilastik.features.feature_extractor import FeatureExtractor
from webilastik.features.ilp_filter import IlpFilter
from webilastik.classifiers.pixel_classifier import PixelClassifier, VigraPixelClassifier
from webilastik.annotations import Annotation
from uuid import uuid4, UUID
from collections import defaultdict

SlotValue = TypeVar('SlotValue')


class AppletDAG:
    def __init__(self):
        self.adjacencies : Dict["Applet", Set["Applet"]] = defaultdict(set)

    def register_connection(self, source: "Applet", sink: "Applet"):
        self.adjacencies[source].add(sink)

    def refresh_downstream_from(self, applet: "Applet"):
        for child in self.adjacencies[applet]:
            pass


class Applet(ABC):
    def __init__(self, inbound_slots: List["Slot"]):
        self.applet_id = uuid4()
        self.children : Set["Applet"] = set()
        for slot in inbound_slots:
            slot.owner.register_child(self)
        self.refresh()

    def register_child(self, child: "Applet"):
        self.children.add(child)

    def __hash__(self) -> int:
        return hash(self.applet_id)

    def refresh(self):
        self.do_refresh()
        for child in self.children:
            try:
                child.refresh()
            except NotReadyException:
                pass

    def do_refresh(self):
        pass


class NotReadyException(Exception):
    pass


class Slot(Generic[SlotValue]):
    def __init__(self, owner: Applet, data_provider: Callable[[], Optional[SlotValue]]):
        self.owner = owner
        self.data_provider = data_provider

    def __call__(self) -> SlotValue:
        out = self.data_provider()
        if out is None:
            raise NotReadyException
        return out


class FeatureSelectionApplet(Applet):
    def __init__(self):
        self.feature_extractors: List[FeatureExtractor] = []
        super().__init__(inbound_slots=[])

    def clear_feature_extractors(self) -> None:
        self.feature_extractors = []
        self.refresh()

    def add_feature_extractors(self, extractors: List[IlpFilter]):
        # FIXME: sort features to calculate in identical fashion to clasic ilastik
        for extractor in extractors:
            if extractor in self.feature_extractors:
                raise ValueError(f"Feature Extractor {extractor} is already present in this Workflow")
            # for lane in self.lanes:
            #     if not extractor.is_applicable_to(lane.RawData.datasource):
            #         raise ValueError(f"Feature {extractor} is not applicable to {lane.RawData.datasource}")
        self.feature_extractors += extractors
        self.refresh()

    @property
    def feature_extractor_slot(self) -> Slot[List[FeatureExtractor]]:
        return Slot(self, lambda : self.feature_extractors[:])


class PixelClassificationApplet(Applet):
    def __init__(
        self,
        *,
        feature_extractors_inslot: Slot[List[FeatureExtractor]],
        annotations_inslot: Slot[List[Annotation]]
    ):
        self.feature_extractors_inslot = feature_extractors_inslot
        self.annotations_inslot = annotations_inslot
        self.pixel_classifier: Optional[PixelClassifier] = None
        super().__init__(inbound_slots=[feature_extractors_inslot, annotations_inslot])

    def do_refresh(self):
        feature_extractors = self.feature_extractors_inslot()
        annotations = self.annotations_inslot()
        self.pixel_classifier = VigraPixelClassifier.train(
            annotations=annotations,
            feature_extractors=feature_extractors
        )

    @property
    def pixel_classifier_slot(self) -> Slot[PixelClassifier]:
        return Slot(owner=self, data_provider=lambda : self.pixel_classifier)