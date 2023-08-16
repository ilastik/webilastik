import json
from typing import Iterable, Optional, Tuple, Sequence, Set
from ndstructs.utils.json_serializable import JsonObject, JsonValue
from webilastik.datasource import DataSource
from webilastik.server.rpc.dto import FeatureSelectionAppletStateDto, MessageParsingError, SetFeatureExtractorsParamsDto

from webilastik.ui.applet import Applet, AppletOutput, CascadeOk, CascadeResult, UserCancelled, UserPrompt, applet_output, cascade
from webilastik.features.ilp_filter import IlpDifferenceOfGaussians, IlpFilter, IlpFilterCollection, IlpGaussianGradientMagnitude, IlpGaussianSmoothing, IlpHessianOfGaussianEigenvalues, IlpLaplacianOfGaussian, IlpStructureTensorEigenvalues
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError

class FeatureSelectionApplet(Applet):
    def __init__(
        self,
        name: str,
        *,
        feature_extractors: "IlpFilterCollection | None" = None,
        datasources: AppletOutput[Set[DataSource]]
    ):
        if feature_extractors is None:
            self._filter_collection = IlpFilterCollection.all()
        else:
            self._filter_collection = feature_extractors
        self._in_datasources = datasources

        super().__init__(name=name)

    def take_snapshot(self) -> IlpFilterCollection:
        return self._filter_collection

    def restore_snaphot(self, snapshot: IlpFilterCollection):
        self._filter_collection = snapshot

    @applet_output
    def feature_extractors(self) -> IlpFilterCollection:
        return self._filter_collection

    @cascade(refresh_self=True)
    def set_feature_extractors(self, user_prompt: UserPrompt, feature_extractors: Iterable[IlpFilter]) -> CascadeResult:
        self._filter_collection = IlpFilterCollection(set(feature_extractors))
        return CascadeOk()

    def refresh(self, user_prompt: UserPrompt) -> CascadeResult:
        incompatible_extractors : Set[IlpFilter] = set()

        for extractor in self._filter_collection.filters:
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
        return CascadeOk()

class WsFeatureSelectionApplet(WsApplet, FeatureSelectionApplet):
    def _get_json_state(self) -> JsonValue:
        return FeatureSelectionAppletStateDto(
            feature_extractors=tuple(extractor.to_dto() for extractor in self._filter_collection.filters)
        ).to_json_value()

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        if method_name == "set_feature_extractors":
            params = SetFeatureExtractorsParamsDto.from_json_value(arguments)
            if isinstance(params, MessageParsingError):
                return UsageError(str(params)) #FIXME: this is a bug, not a usage error
            return UsageError.check(self.set_feature_extractors(
                user_prompt=user_prompt, feature_extractors=[IlpFilter.from_dto(m) for m in params.feature_extractors]
            ))
        raise ValueError(f"Invalid method name: '{method_name}'")