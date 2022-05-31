import json
from typing import Iterable, Tuple, Sequence, Set
from webilastik.datasource import DataSource

from webilastik.ui.applet import Applet, AppletOutput, PropagationOk, PropagationResult, UserCancelled, UserPrompt, applet_output, user_interaction
from webilastik.features.ilp_filter import IlpFilter

class FeatureSelectionApplet(Applet):
    def __init__(self, name: str, *, datasources: AppletOutput[Set[DataSource]]):
        self._in_datasources = datasources
        self._feature_extractors: Set[IlpFilter] = set()
        super().__init__(name=name)

    def take_snapshot(self) -> Tuple[IlpFilter, ...]:
        return tuple(self._feature_extractors)

    def restore_snaphot(self, snapshot: Tuple[IlpFilter, ...]) -> None:
        self._feature_extractors = set(snapshot)

    @applet_output
    def feature_extractors(self) -> Sequence[IlpFilter]:
        return sorted(self._feature_extractors, key=lambda fe: json.dumps(fe.to_json_data())) #FIXME

    def _set_feature_extractors(self, user_prompt: UserPrompt, feature_extractors: Iterable[IlpFilter]) -> PropagationResult:
        candidate_extractors = set(feature_extractors)
        incompatible_extractors : Set[IlpFilter] = set()

        for extractor in candidate_extractors:
            for ds in self._in_datasources():
                if not extractor.is_applicable_to(ds):
                    incompatible_extractors.add(extractor)
                    break

        if incompatible_extractors and not user_prompt(
            message=(
                "The following feature extractors are incompatible with your datasources:\n"
                "\n".join(str(extractor) for extractor in incompatible_extractors)
            ),
            options={"Drop features": True, "Abort change": False}
        ):
            return UserCancelled()
        self._feature_extractors = candidate_extractors.difference(incompatible_extractors)
        return PropagationOk()

    @user_interaction(refresh_self=True)
    def add_feature_extractors(self, user_prompt: UserPrompt, feature_extractors: Iterable[IlpFilter]) -> PropagationResult:
        return self._set_feature_extractors(
            user_prompt=user_prompt,
            feature_extractors=self._feature_extractors.union(feature_extractors)
        )

    @user_interaction(refresh_self=True)
    def remove_feature_extractors(self, user_prompt: UserPrompt, feature_extractors: Iterable[IlpFilter]) -> PropagationResult:
        return self._set_feature_extractors(
            user_prompt=user_prompt,
            feature_extractors=self._feature_extractors.difference(feature_extractors)
        )

    def on_dependencies_changed(self, user_prompt: UserPrompt) -> PropagationResult:
        return self._set_feature_extractors(user_prompt=user_prompt, feature_extractors=self._feature_extractors)
