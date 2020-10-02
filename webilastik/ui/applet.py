from abc import ABC, abstractmethod
import typing
from typing import List, Optional, Callable, Any, Generic, TypeVar, Dict, Set
import typing_extensions
from typing_extensions import Protocol

from webilastik.features.feature_extractor import FeatureExtractor
from webilastik.features.ilp_filter import IlpFilter
from webilastik.classifiers.pixel_classifier import PixelClassifier, VigraPixelClassifier
from webilastik.annotations import Annotation
from uuid import uuid4, UUID
from collections import defaultdict
from functools import wraps

import inspect
from inspect import _ParameterKind



class CancelledException(Exception):
    pass

CONFIRMER = Callable[[str], bool]
SV = TypeVar('SV')

def noop_confirmer(msg: str) -> bool:
    return True


class Slot(Generic[SV]):
    def __init__(self, *, owner: "Applet", value: Optional[SV] = None):
        self.owner = owner
        self.subscribers : List["Applet"] = []
        self._value = value

    def get_downstream_applets(self) -> List["Applet"]:
        """Returns a list of the topologically sorted applets consuming this slot"""
        out : Set["Applet"] = set(self.subscribers)
        for applet in self.subscribers:
            out.update(applet.get_downstream_applets())
        return sorted(out)

    def subscribe(self, applet: "Applet"):
        self.subscribers.append(applet)

    def __call__(self) -> Optional[SV]:
        return self._value

    #this should be called by e.g. the GUI
    def set_propagate(self, value: Optional[SV], confirmer: CONFIRMER):
        old_value = self._value
        try:
            self.owner.cascade_refresh(confirmer)
        except Exception:
            self._value = old_value
            raise

    #this should be use inside Applet.update_outputs
    def _set(self, value: Optional[SV]):
        self._value


class Applet(ABC):
    def __init__(
        self,
        *,
        borrowed_slots: List["Slot"],
        owned_slots: List["Slot"],
    ):
        self.owned_slots = owned_slots
        self.upstream_applets : Set[Applet] = {in_slot.owner for in_slot in borrowed_slots}
        for borrowed_slot in borrowed_slots:
            self.upstream_applets.update(borrowed_slot.owner.upstream_applets)
            borrowed_slot.subscribe(self)

    def get_downstream_applets(self) -> List["Applet"]:
        """Returns a list of the topologically sorted descendants of this applet"""
        out : Set[Applet] = set()
        for output_slot in self.owned_slots:
            out.update(output_slot.get_downstream_applets())
        return sorted(out)

    def __lt__(self, other: "Applet") -> bool:
        return self in other.upstream_applets

    def take_snapshot(self):
        return {slot: slot() for slot in self.owned_slots}

    def restore_snaphot(self, snap):
        for slot, saved_value in snap.items():
            slot._set(saved_value)

    @typing_extensions.final
    def cascade_refresh(self, confirmer: CONFIRMER):
        """
        The good thing of having Applet.refresh is that it gives the Applet a chance to coordinate updating slots.
        It also prevents multiple warnings coming from multiple slots of the same Applet -- is that bad, though?

        The lame part is that things don't work automatically once a slot is updated; it depends on devs implementing update_outputs
        correctly (setting slots correctly, returning the modified slots accordingly)

        Also... what is supposed to trigger  this method? Propbly ValueSlot.setValue is enough for triggering the first refresh()
        """
        snapshots = {}
        try:
            for applet in [self] + self.get_downstream_applets():
                snapshots[applet] = applet.take_snapshot()
                applet.update_outputs(confirmer)
        except Exception:
            for applet, snap in snapshots.items():
                applet.restore_snaphot(snap)
            raise

    @abstractmethod
    def update_outputs(self, confirmer: CONFIRMER) -> List[Slot]:
        pass


class FeatureSelectionApplet(Applet):
    def __init__(self):
        self.feature_extractors = Slot[List[IlpFilter]](owner=self)
        super().__init__(borrowed_slots=[], owned_slots=[self.feature_extractors])

    def clear_feature_extractors(self, *, confirmer: CONFIRMER = noop_confirmer) -> None:
        self.feature_extractors.set_propagate(None, confirmer=confirmer)

    def add_feature_extractors(self, value: List[IlpFilter], confirmer: CONFIRMER = noop_confirmer):
        # FIXME: sort features to calculate in identical fashion to clasic ilastik
        current_extractors = self.feature_extractors()
        for extractor in value:
            if extractor in current_extractors:
                raise ValueError(f"Feature Extractor {extractor} is already present in this Workflow")
            # for lane in self.lanes:
            #     if not extractor.is_applicable_to(lane.RawData.datasource):
            #         raise ValueError(f"Feature {extractor} is not applicable to {lane.RawData.datasource}")
        self.feature_extractors.set_propagate(current_extractors + value, confirmer=confirmer)


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
        would_take_long = True
        if would_take_long:
            if not confirmer("Are you sure you want to retrain the classifier? This can take a few minutes or whatever"):
                raise CancelledException("bla")
        return  VigraPixelClassifier.train(
            annotations=annotations,
            feature_extractors=feature_extractors
        )