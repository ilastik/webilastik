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
    def __init__(self, *, owner: "Applet"):
        self.owner = owner
        self.downstream_applets : List["Applet"] = []
        # self.value is Optional because it may not have been set by the user or generated by the applet
        self._value : Optional[SV] = None

    def subscribe(self, applet: "Applet"):
        self.downstream_applets.append(applet)

    def __call__(self) -> Optional[SV]:
        return self._value

    @abstractmethod
    def refresh(self, confirmer: CONFIRMER):
        pass

    def _update_and_propagate(self, new_value: SV, confirmer: CONFIRMER):
        if self._value == new_value: # type: ignore
            return
        old_value = self._value
        self._value = new_value
        for applet in self.downstream_applets:
            for out_slot in applet.output_slots:
                try:
                    out_slot.refresh(confirmer)
                except Exception:
                    self.value = old_value
                    raise


class DerivedSlot(Slot[SV]):
    def __init__(
        self,
        *,
        owner: "Applet",
        value_generator: Callable[[], Optional[SV]],
        before_recompute_warning: Optional[str= = None,
        before_modify_warning: Optional[str] = None,
    ):
        self.value_generator = value_generator
        self.confirmation_message = confirmation_message
        super().__init__(owner=owner)

    def refresh(self, confirmer: CONFIRMER):
        if self.confirmation_message and confirmer(self.confirmation_message):
            raise CancelledException("User cancelled when propted with {self.confirmation_message}")
        self._update_and_propagate(self.value_generator(), confirmer=confirmer)


    def _update_and_propagate(self, new_value: SV, confirmer: CONFIRMER):
        if self._value == new_value: # type: ignore
            return
        old_value = self._value
        self._value = new_value
        for applet in self.downstream_applets:
            for out_slot in applet.output_slots:
                try:
                    out_slot.refresh(confirmer)
                except Exception:
                    self.value = old_value
                    raise




class ValueSlot(Slot[SV]):
    def __init__(self, *, owner: "Applet", value: Optional[SV] = None):
        super().__init__(owner=owner)
        self._value = value

    def setValue(self, value: Optional[SV], confirmer: CONFIRMER):
        self._update_and_propagate(value, confirmer)

    def refresh(self, confirmer: CONFIRMER):
        pass



class Applet(ABC):
    def __init__(
        self,
        *,
        input_slots: List["Slot"],
        output_slots: List["Slot"],
    ):
        self.output_slots = output_slots
        self.ancestors : Set[Applet] = {in_slot.owner for in_slot in input_slots}
        for input_slot in input_slots:
            self.ancestors.update(input_slot.owner.ancestors)
            input_slot.subscribe(self)

    def get_descendants(self) -> Set["Applet"]:
        out : Set[Applet] = set()
        for output_slot in self.output_slots:
            out.update(output_slot.downstream_applets)
        return out

    def __lt__(self, other: "Applet") -> bool:
        return self in other.ancestors

    def refresh(self, confirmer: CONFIRMER):
        for output_slot in self.output_slots:
            output_slot.refresh(confirmer)


class FeatureSelectionApplet(Applet):
    def __init__(self):
        self.feature_extractors = ValueSlot[List[IlpFilter]](owner=self)
        super().__init__(input_slots=[], output_slots=[self.feature_extractors])

    def clear_feature_extractors(self, *, confirmer: CONFIRMER = noop_confirmer) -> None:
        self.feature_extractors.setValue(None, confirmer=confirmer)

    def add_feature_extractors(self, value: List[IlpFilter], confirmer: CONFIRMER = noop_confirmer):
        # FIXME: sort features to calculate in identical fashion to clasic ilastik
        for extractor in value:
            if extractor in self.feature_extractors():
                raise ValueError(f"Feature Extractor {extractor} is already present in this Workflow")
            # for lane in self.lanes:
            #     if not extractor.is_applicable_to(lane.RawData.datasource):
            #         raise ValueError(f"Feature {extractor} is not applicable to {lane.RawData.datasource}")
        self.feature_extractors.setValue(self.feature_extractors() + value, confirmer=confirmer)


class PixelAnnotationApplet(Applet):
    def __init__(self):
        self.annotations = ValueSlot[List[Annotation]](owner=self)
        super().__init__(input_slots=[], output_slots=[self.annotations])


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
            confirmation_message="Are you sre you want to retrain the classifier?",
            value_generator=self.create_pixel_classifier
        )
        super().__init__(
            input_slots=[feature_extractors_inslot, annotations_inslot],
            output_slots=[self.pixel_classifier]
        )

    def create_pixel_classifier(self, confirmer: CONFIRMER = noop_confirmer) -> Optional[PixelClassifier]:
        feature_extractors = self.feature_extractors_inslot()
        annotations = self.annotations_inslot()
        if not feature_extractors or not annotations:
            return None
        would_take_long_to_compute = True
        if would_take_long_to_compute:
            if not confirmer("Are you sure you want to retrain the classifier? This can take a while"):
                return None

        return VigraPixelClassifier.train(
            annotations=annotations,
            feature_extractors=feature_extractors,
        )