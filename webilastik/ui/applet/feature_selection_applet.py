import json
from typing import Iterable, Optional, Tuple, Sequence, Set
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonArray, ensureJsonObject, ensureJsonString
from webilastik.datasource import DataSource
from webilastik.features.channelwise_fastfilters import DifferenceOfGaussians, GaussianGradientMagnitude, GaussianSmoothing, HessianOfGaussianEigenvalues, LaplacianOfGaussian, StructureTensorEigenvalues

from webilastik.ui.applet import Applet, AppletOutput, PropagationOk, PropagationResult, UserCancelled, UserPrompt, applet_output, user_interaction
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

class WsFeatureSelectionApplet(WsApplet, FeatureSelectionApplet):
    def _item_from_json_data(self, data: JsonValue) -> IlpFilter:
        data_dict = ensureJsonObject(data)
        class_name = ensureJsonString(data_dict.get("__class__"))
        if class_name == StructureTensorEigenvalues.__name__:
            return StructureTensorEigenvalues.from_json_data(data)
        if class_name == GaussianGradientMagnitude.__name__:
            return GaussianGradientMagnitude.from_json_data(data)
        if class_name == GaussianSmoothing.__name__:
            return GaussianSmoothing.from_json_data(data)
        if class_name == DifferenceOfGaussians.__name__:
            return DifferenceOfGaussians.from_json_data(data)
        if class_name == HessianOfGaussianEigenvalues.__name__:
            return HessianOfGaussianEigenvalues.from_json_data(data)
        if class_name == LaplacianOfGaussian.__name__:
            return LaplacianOfGaussian.from_json_data(data)
        raise ValueError(f"Could not convert {data} into a Feature Extractor")

    def _get_json_state(self) -> JsonValue:
        return {"feature_extractors": tuple(extractor.to_json_data() for extractor in self.feature_extractors())}

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        raw_feature_array = ensureJsonArray(arguments.get("feature_extractors"))
        feature_extractors = [self._item_from_json_data(raw_feature) for raw_feature in raw_feature_array]

        if method_name == "add_feature_extractors":
            return UsageError.check(self.add_feature_extractors(user_prompt=user_prompt, feature_extractors=feature_extractors))
        if method_name == "remove_feature_extractors":
            return UsageError.check(self.remove_feature_extractors(user_prompt, feature_extractors))
        raise ValueError(f"Invalid method name: '{method_name}'")