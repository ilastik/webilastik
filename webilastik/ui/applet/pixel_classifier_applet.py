# pyright: strict

from concurrent.futures import Future, Executor
from dataclasses import dataclass
from functools import partial
import threading
from typing import Any, Callable, Literal, Optional, Sequence, Dict, Union, Mapping, Tuple

import numpy as np

from webilastik.ui.applet  import Applet, AppletOutput, CascadeOk, CascadeResult, UserPrompt, applet_output, cascade
from webilastik.annotations.annotation import Annotation, Color
from webilastik.features.ilp_filter import IlpFilter
from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.ui.usage_error import UsageError


Classifier = VigraPixelClassifier[IlpFilter]
ColorMap = Dict[Color, np.uint8]
Description = Literal["disabled", "waiting for inputs", "training", "ready", "error"]

@dataclass
class _State:
    live_update: bool
    classifier: "Future[Classifier | ValueError] | Classifier | None | BaseException"
    generation: int

    @property
    def description(self) -> Description:
        if not self.live_update:
            return "disabled"
        if self.classifier is None:
            return "waiting for inputs"
        if isinstance(self.classifier, Future):
            return "training"
        if isinstance(self.classifier, Exception):
            return "error"
        return "ready"

    def updated_with(
        self,
        *,
        classifier: "Future[Classifier | ValueError] | Classifier | None | BaseException",
        live_update: Optional[bool] = None,
        generation: Optional[int] = None,
    ) -> "_State":
        if self.classifier != classifier and isinstance(self.classifier, Future):
            _ = self.classifier.cancel()

        return _State(
            classifier=classifier,
            live_update=live_update if live_update is not None else self.live_update,
            generation=generation if generation is not None else self.generation + 1,
        )

Interaction = Callable[[], Optional[UsageError]]

class PixelClassificationApplet(Applet):
    def __init__(
        self,
        name: str,
        *,
        feature_extractors: AppletOutput[Sequence[IlpFilter]],
        label_classes: AppletOutput[Mapping[Color, Sequence[Annotation]]],
        executor: Executor,
        on_async_change: Callable[[], Any],
        pixel_classifier: "VigraPixelClassifier[IlpFilter] | None",
    ):
        self._in_feature_extractors = feature_extractors
        self._in_label_classes = label_classes
        self.executor = executor
        self.on_async_change = on_async_change

        self._state: _State = _State(
            live_update=False,
            classifier=pixel_classifier,
            generation=0,
        )

        self.lock = threading.Lock()
        super().__init__(name=name)

    def take_snapshot(self) -> _State:
        with self.lock:
            return self._state

    def restore_snaphot(self, snapshot: _State) -> None:
        with self.lock:
            self._state = snapshot

    @applet_output
    def pixel_classifier(self) -> Optional[VigraPixelClassifier[IlpFilter]]:
        classifier = self._state.classifier
        return classifier if isinstance(classifier, VigraPixelClassifier) else None #FIXME?

    @applet_output
    def generational_pixel_classifier(self) -> "Tuple[VigraPixelClassifier[IlpFilter], int] | None":
        with self.lock:
            classifier = self._state.classifier
            if not isinstance(classifier, VigraPixelClassifier):
                return None
            return (classifier, self._state.generation)

    def refresh(self, user_prompt: UserPrompt) -> CascadeResult:
        with self.lock:
            if not self._state.live_update:
                # annotations or features changed, so classifier is stale
                self._state = self._state.updated_with(classifier=None)
                return CascadeOk()

            label_classes = self._in_label_classes()
            feature_extractors = self._in_feature_extractors()
            if sum(len(labels) for labels in label_classes.values()) == 0 or not feature_extractors:
                # annotations or features changed, so classifier is stale
                self._state = self._state.updated_with(classifier=None)
                return CascadeOk()

            classifier_future = self.executor.submit(
                partial(Classifier.train, feature_extractors), tuple(label_classes.values())
            )
            previous_state = self._state = self._state.updated_with(classifier=classifier_future)

        def on_training_ready(classifier_future: Future["VigraPixelClassifier[IlpFilter] | ValueError"]):
            if classifier_future.cancelled():
                print(f"{self.__class__.__name__} ({self.name}) Training was cancelled....")
                return
            classifier_result = classifier_future.exception() or classifier_future.result()
            propagation_result = self._set_classifier(user_prompt, classifier_result, previous_state.generation)
            if not propagation_result.is_ok():
                print(f"!!!!!! Training failed: {propagation_result}")
            self.on_async_change()
        classifier_future.add_done_callback(on_training_ready)

        return CascadeOk()

    @cascade(refresh_self=False)
    def _set_classifier(self, user_prompt: UserPrompt, classifier: Union[Classifier, BaseException], generation: int) -> CascadeResult:
        with self.lock:
            if self._state.generation == generation:
                self._state = self._state.updated_with(classifier=classifier)
        return CascadeOk()

    @cascade(refresh_self=True)
    def set_live_update(self, user_prompt: UserPrompt, live_update: bool) -> CascadeResult:
        with self.lock:
            self._state = self._state.updated_with(classifier=self._state.classifier, live_update=live_update)
        return CascadeOk()
