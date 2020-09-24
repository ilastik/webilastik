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



class NotReadyException(Exception):
    pass

class CancelledException(Exception):
    pass

SlotValue = TypeVar('SlotValue')
class Slot(Generic[SlotValue]):
    def __init__(self, owner: "Applet", data_provider: Callable[[], Optional[SlotValue]]):
        self.owner = owner
        self.data_provider = data_provider

    def __call__(self) -> SlotValue:
        out = self.data_provider()
        if out is None:
            raise NotReadyException
        return out




CONFIRMATION_CALLBACK = Callable[[str], bool]
T = TypeVar("T")
APPLET = TypeVar("APPLET", covariant=True, bound="Applet")

class AppletPropSetter(Protocol, Generic[APPLET, T]):
    def __call__(self: APPLET, *, value: T, confirmation_callback: CONFIRMATION_CALLBACK) -> None:
        ...

class AppletPropResetter(Protocol, Generic[APPLET]):
    def __call__(self: APPLET, *, confirmation_callback: CONFIRMATION_CALLBACK) -> None:
        ...


#APPLET_PROP_SETTER = Callable[[SELF_APPLET, T, CONFIRMATION_CALLBACK], None]
#APPLET_PROP_RESETTER = Callable[[SELF_APPLET, CONFIRMATION_CALLBACK], None]

@typing.overload
def autopropagate(method: AppletPropResetter) -> AppletPropResetter:
    ...

@typing.overload
def autopropagate(method: AppletPropSetter) -> AppletPropSetter:
    ...

def autopropagate(method):
    confirmation_callback_param = inspect.signature(method).parameters.get("confirmation_callback")
    assert (
        confirmation_callback_param and
        confirmation_callback_param.annotation == CONFIRMATION_CALLBACK and
        confirmation_callback_param.kind == _ParameterKind.KEYWORD_ONLY #type: ignore
    ), f"methods with @autopropagate must have a keyword-only argument 'confirmation_callback: {CONFIRMATION_CALLBACK}''"

    def wrapper(self: Applet, *args, confirmation_callback: CONFIRMATION_CALLBACK = lambda msg: True, **kwargs):
        snapshots : Dict[Applet, Dict[str, Any]] = {} #applet -> snapshot

        snapshots[self] = self.take_snapshot()
        method(self, *args, **kwargs)

        for applet in [self] + list(self.children):
            if applet != self:
                snapshots[applet] = applet.take_snapshot()
            try:
                applet.refresh_outputs(confirmation_callback=confirmation_callback)
            except CancelledException: # changes would be destructive and user did not confirm
                for applet, snap in snapshots.items():
                    applet.restore_snapshot(snap)
                raise
            except NotReadyException: #some inbound slot was not ready, so i guess no harm was done?
                pass
    return wrapper


class Applet(ABC):
    def __init__(
        self,
        *,
        inbound_slots: List["Slot"],
        required_confirmation_message: Optional[str] = None,
    ):
        self.children : Set["Applet"] = set()
        self.required_confirmation_message = required_confirmation_message
        for slot in inbound_slots:
            slot.owner.register_child(self)
        try:
            self.do_refresh_outputs()
        except NotReadyException:
            pass

    def __str__(self) -> str:
        return self.__class__.__name__

    def register_child(self, child: "Applet"):
        self.children.add(child)

    def take_snapshot(self) -> Any:
        print(f">>>> Saving snapshot for {self}")
        return self.__dict__.copy()

    def restore_snapshot(self, snap: Dict[str, Any]):
        print(f"<<<< Loading snapshot for {self}")
        self.__dict__.update(snap)

    @typing_extensions.final
    def refresh_outputs(self, confirmation_callback: CONFIRMATION_CALLBACK = lambda msg: True):
        """Re-reads inputs, recomputes values. Throws CancelledException

        If update is destructive or costly, confirmation is asked through confirmation_callback.
        Raises a CancelledException if the user does not confirm
        """
        if self.required_confirmation_message is not None:
            if not confirmation_callback(self.required_confirmation_message):
                raise CancelledException(f"User cancelled changes for {self}")
        self.reset_values()
        self.do_refresh_outputs()

    def do_refresh_outputs(self):
        pass

    @abstractmethod
    def reset_values(self):
        pass


class FeatureSelectionApplet(Applet):
    def __init__(self):
        self.feature_extractors: List[FeatureExtractor] = []
        super().__init__(inbound_slots=[])

    def reset_values(self):
        pass

    @autopropagate
    def clear_feature_extractors(self, *, confirmation_callback: CONFIRMATION_CALLBACK = lambda msg: True) -> None:
        self.feature_extractors = []

    @autopropagate
    def add_feature_extractors(self, *, value: List[IlpFilter], confirmation_callback: CONFIRMATION_CALLBACK = lambda msg: True):
        # FIXME: sort features to calculate in identical fashion to clasic ilastik
        for extractor in value:
            if extractor in self.feature_extractors:
                raise ValueError(f"Feature Extractor {extractor} is already present in this Workflow")
            # for lane in self.lanes:
            #     if not extractor.is_applicable_to(lane.RawData.datasource):
            #         raise ValueError(f"Feature {extractor} is not applicable to {lane.RawData.datasource}")
        self.feature_extractors += value

    @property
    def feature_extractor_outslot(self) -> Slot[List[FeatureExtractor]]:
        return Slot(self, lambda : self.feature_extractors[:] or None)


class PixelAnnotationApplet(Applet):
    def __init__(self):
        self.annotations : List[Annotation] = []
        super().__init__(inbound_slots=[])

    def reset_values(self):
        pass

    @property
    def annotations_outslot(self) -> Slot[List[Annotation]]:
        return Slot(self, lambda : self.annotations[:] or None)

class PixelClassificationApplet(Applet):
    def __init__(
        self,
        *,
        feature_extractors_inslot: Slot[List[FeatureExtractor]],
        annotations_inslot: Slot[List[Annotation]],
    ):
        self.feature_extractors_inslot = feature_extractors_inslot
        self.annotations_inslot = annotations_inslot
        self.pixel_classifier: Optional[PixelClassifier] = None
        super().__init__(
            inbound_slots=[feature_extractors_inslot, annotations_inslot],
            required_confirmation_message="Do you want to retrain the classifier?"
        )

    def reset_values(self):
        self.pixel_classifier = None

    def do_refresh_outputs(self):
        feature_extractors = self.feature_extractors_inslot()
        annotations = self.annotations_inslot()
        self.pixel_classifier = VigraPixelClassifier.train(
            annotations=annotations,
            feature_extractors=feature_extractors
        )

    @property
    def pixel_classifier_slot(self) -> Slot[PixelClassifier]:
        return Slot(owner=self, data_provider=lambda : self.pixel_classifier)
