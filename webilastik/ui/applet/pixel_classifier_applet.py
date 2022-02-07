# pyright: strict

from concurrent.futures import Future
from dataclasses import dataclass
from functools import partial
import threading
from typing import Any, Callable, Literal, Optional, Sequence, Dict, Union
import textwrap

import numpy as np
from webilastik.scheduling.hashing_executor import HashingExecutor

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
    classifier: Union[Future[Classifier], Classifier, None, Exception]
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
        classifier: Union[Future[Classifier], Classifier, None, Exception],
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
        runner: HashingExecutor,
        enqueue_interaction: Callable[[Interaction], Any],
    ):
        self._in_feature_extractors = feature_extractors
        self._in_annotations = annotations
        self.runner = runner
        self.enqueue_interaction = enqueue_interaction

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

            classifier_future = self.runner.submit(
                partial(Classifier.train, feature_extractors), annotations
            )
            previous_state = self._state = self._state.updated_with(classifier=classifier_future)

        def interaction() -> Optional[UsageError]:
            try:
                classifier = classifier_future.result()
            except Exception as e:
                classifier = e
            result = self._set_classifier(user_prompt, classifier, previous_state.generation)
            return UsageError.check(result)

        classifier_future.add_done_callback(lambda _: self.enqueue_interaction(interaction))
        return PropagationOk()

    @user_interaction(refresh_self=False)
    def _set_classifier(self, user_prompt: UserPrompt, classifier: Union[Classifier, Exception], generation: int) -> PropagationResult:
        with self.lock:
            if self._state.generation == generation:
                self._state = self._state.updated_with(classifier=classifier)
                if not isinstance(classifier, Exception):
                    _ = classifier.__getstate__() #warm up pickle cache?
        return PropagationOk()

    @user_interaction(refresh_self=True)
    def set_live_update(self, user_prompt: UserPrompt, live_update: bool) -> PropagationResult:
        with self.lock:
            self._state = self._state.updated_with(classifier=self._state.classifier, live_update=live_update)
        return PropagationOk()

    # def get_ilp_classifier_feature_names(self) -> Iterator[bytes]:
    #     # FIXME: annotations can be empty!
    #     num_input_channels = self._in_annotations()[0].raw_data.shape.c #FIXME: all lanes always have same c?
    #     for fe in sorted(self._in_feature_extractors(), key=lambda ex: FeatureSelectionApplet.ilp_feature_names.index(ex.__class__.__name__)):
    #         for c in range(num_input_channels * fe.channel_multiplier):
    #             name_and_channel = fe.ilp_name + f" [{c}]"
    #             yield name_and_channel.encode("utf8")

    # def get_classifier_ilp_data(self) -> Mapping[str, Any]:
    #     classifier = self._pixel_classifier
    #     if classifier is None:
    #         return {} # FIXME
    #     out = classifier.get_forest_data()
    #     feature_names: Iterator[bytes] = self.get_ilp_classifier_feature_names()
    #     out["feature_names"] = np.asarray(list(feature_names))
    #     out[
    #         "pickled_type"
    #     ] = b"clazyflow.classifiers.parallelVigraRfLazyflowClassifier\nParallelVigraRfLazyflowClassifier\np0\n."
    #     out["known_labels"] = np.asarray(classifier.classes).astype(np.uint32)
    #     return out

    # @property
    # def ilp_data(self) -> Dict[str, Any]:
    #     out = {
    #         "Bookmarks": {"0000": []},
    #         "StorageVersion": "0.1",
    #         "ClassifierFactory": DEFAULT_ILP_CLASSIFIER_FACTORY,
    #     }
    #     classifier_forests = self.get_classifier_ilp_data()
    #     if classifier_forests:
    #         out["ClassifierForests"] = classifier_forests

    #     out["LabelSets"] = labelSets = {"labels000": {}}  # empty labels still produce this in classic ilastik
    #     color_map = self.color_map()
    #     datasources = {a.raw_data for a in self._in_annotations()} # FIXME: is order important?
    #     for lane_idx, datasource in enumerate(datasources):
    #         lane_annotations = [annot for annot in self._in_annotations() if annot.raw_data == datasource]
    #         label_data = Annotation.dump_as_ilp_data(lane_annotations, color_map=color_map)
    #         labelSets[f"labels{lane_idx:03d}"] = label_data
    #     out["LabelColors"] = np.asarray([color.rgba[:-1] for color in color_map.keys()], dtype=np.int64)
    #     out["PmapColors"] = out["LabelColors"]
    #     out["LabelNames"] = np.asarray([color.name.encode("utf8") for color in color_map.keys()])
    #     return out
