# pyright: strict

from concurrent.futures import Future, Executor
from dataclasses import dataclass
from functools import partial
import threading
from typing import Any, Callable, Literal, Optional, Sequence, Dict, Union
import textwrap

import numpy as np

from webilastik.ui.applet  import Applet, AppletOutput, PropagationOk, PropagationResult, UserPrompt, applet_output, user_interaction
from webilastik.annotations.annotation import Annotation, Color
from webilastik.features.ilp_filter import IlpFilter
from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.ui.usage_error import UsageError


DEFAULT_ILP_CLASSIFIER_FACTORY = textwrap.dedent(
        """
        ccopy_reg
        _reconstructor
        p0
        (clazyflow.classifiers.parallelVigraRfLazyflowClassifier
        ParallelVigraRfLazyflowClassifierFactory
        p1
        c__builtin__
        object
        p2
        Ntp3
        Rp4
        (dp5
        VVERSION
        p6
        I2
        sV_num_trees
        p7
        I100
        sV_label_proportion
        p8
        NsV_variable_importance_path
        p9
        NsV_variable_importance_enabled
        p10
        I00
        sV_kwargs
        p11
        (dp12
        sV_num_forests
        p13
        I8
        sb."""[
            1:
        ]
    ).encode("utf8")

Classifier = VigraPixelClassifier[IlpFilter]
ColorMap = Dict[Color, np.uint8]
Description = Literal["disabled", "waiting for inputs", "training", "ready", "error"]

@dataclass
class _State:
    live_update: bool
    classifier: Union[Future[Classifier], Classifier, None, BaseException]
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
        classifier: Union[Future[Classifier], Classifier, None, BaseException],
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
        annotations: AppletOutput[Sequence[Annotation]],
        executor: Executor,
        on_async_change: Callable[[], Any],
    ):
        self._in_feature_extractors = feature_extractors
        self._in_annotations = annotations
        self.executor = executor
        self.on_async_change = on_async_change

        self._state: _State = _State(
            live_update=False,
            classifier=None,
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

    def on_dependencies_changed(self, user_prompt: UserPrompt) -> PropagationResult:
        with self.lock:
            if not self._state.live_update:
                # annotations or features changed, so classifier is stale
                self._state = self._state.updated_with(classifier=None)
                return PropagationOk()

            annotations = self._in_annotations()
            feature_extractors = self._in_feature_extractors()
            if not annotations or not feature_extractors:
                # annotations or features changed, so classifier is stale
                self._state = self._state.updated_with(classifier=None)
                return PropagationOk()

            classifier_future = self.executor.submit(
                partial(Classifier.train, feature_extractors), annotations
            )
            previous_state = self._state = self._state.updated_with(classifier=classifier_future)

        def on_training_ready(classifier_future: Future[VigraPixelClassifier[IlpFilter]]):
            classifier_result = classifier_future.exception() or classifier_future.result()
            propagation_result = self._set_classifier(user_prompt, classifier_result, previous_state.generation)
            if not propagation_result.is_ok():
                print(f"!!!!!! Training failed: {propagation_result}")
            self.on_async_change()
        classifier_future.add_done_callback(on_training_ready)

        return PropagationOk()

    @user_interaction(refresh_self=False)
    def _set_classifier(self, user_prompt: UserPrompt, classifier: Union[Classifier, BaseException], generation: int) -> PropagationResult:
        with self.lock:
            if self._state.generation == generation:
                self._state = self._state.updated_with(classifier=classifier)
        return PropagationOk()

    @user_interaction(refresh_self=True)
    def set_live_update(self, user_prompt: UserPrompt, live_update: bool) -> PropagationResult:
        with self.lock:
            self._state = self._state.updated_with(classifier=self._state.classifier, live_update=live_update)
        return PropagationOk()
