import json
from typing import Iterable, Optional, Tuple, Sequence, Set
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonArray, ensureJsonObject, ensureJsonString
from webilastik.datasource import DataSource
from webilastik.features.channelwise_fastfilters import DifferenceOfGaussians, GaussianGradientMagnitude, GaussianSmoothing, HessianOfGaussianEigenvalues, LaplacianOfGaussian, StructureTensorEigenvalues

from webilastik.ui.applet import Applet, AppletOutput, CascadeOk, CascadeResult, UserCancelled, UserPrompt, applet_output, cascade
from webilastik.features.ilp_filter import IlpFilter
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError

class FeatureSelectionApplet(Applet):
    def __init__(
        self,
        name: str,
        *,
        feature_extractors: "Set[IlpFilter] | None" = None,
        datasources: AppletOutput[Set[DataSource]]
    ):
        self._in_datasources = datasources
        self._feature_extractors: Set[IlpFilter] = feature_extractors or set()
        super().__init__(name=name)

    def take_snapshot(self) -> Tuple[IlpFilter, ...]:
        return tuple(self._feature_extractors)

    def restore_snaphot(self, snapshot: Tuple[IlpFilter, ...]) -> None:
        self._feature_extractors = set(snapshot)

    @applet_output
    def feature_extractors(self) -> Sequence[IlpFilter]:
        return sorted(self._feature_extractors, key=lambda fe: json.dumps(fe.to_json_value())) #FIXME

    def _set_feature_extractors(self, user_prompt: UserPrompt, feature_extractors: Iterable[IlpFilter]) -> CascadeResult:
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
        return CascadeOk()

    @cascade(refresh_self=True)
    def add_feature_extractors(self, user_prompt: UserPrompt, feature_extractors: Iterable[IlpFilter]) -> CascadeResult:
        return self._set_feature_extractors(
            user_prompt=user_prompt,
            feature_extractors=self._feature_extractors.union(feature_extractors)
        )

    @cascade(refresh_self=True)
    def remove_feature_extractors(self, user_prompt: UserPrompt, feature_extractors: Iterable[IlpFilter]) -> CascadeResult:
        return self._set_feature_extractors(
            user_prompt=user_prompt,
            feature_extractors=self._feature_extractors.difference(feature_extractors)
        )

    def refresh(self, user_prompt: UserPrompt) -> CascadeResult:
        return self._set_feature_extractors(user_prompt=user_prompt, feature_extractors=self._feature_extractors)

class WsFeatureSelectionApplet(WsApplet, FeatureSelectionApplet):
    def _get_json_state(self) -> JsonValue:
        return {"feature_extractors": tuple(extractor.to_json_value() for extractor in self.feature_extractors())}

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        raw_feature_array = ensureJsonArray(arguments.get("feature_extractors"))
        feature_extractors = [IlpFilter.from_json_value(raw_feature) for raw_feature in raw_feature_array]

        if method_name == "add_feature_extractors":
            return UsageError.check(self.add_feature_extractors(user_prompt=user_prompt, feature_extractors=feature_extractors))
        if method_name == "remove_feature_extractors":
            return UsageError.check(self.remove_feature_extractors(user_prompt, feature_extractors))
        raise ValueError(f"Invalid method name: '{method_name}'")