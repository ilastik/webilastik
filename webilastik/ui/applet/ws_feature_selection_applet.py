

from typing import Optional
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonArray, ensureJsonObject, ensureJsonString
from webilastik.features.channelwise_fastfilters import DifferenceOfGaussians, GaussianGradientMagnitude, GaussianSmoothing, HessianOfGaussianEigenvalues, LaplacianOfGaussian, StructureTensorEigenvalues
from webilastik.features.ilp_filter import IlpFilter
from webilastik.ui.applet import UserPrompt
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError


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