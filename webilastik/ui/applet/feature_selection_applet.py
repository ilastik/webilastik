import json
from typing import Iterable, List, Tuple, TypeVar, Sequence, Optional, Dict, Any, Set
from webilastik.datasource import DataSource

import numpy as np

from webilastik.ui.applet import Applet, AppletOutput, PropagationOk, PropagationResult, UserCancelled, UserPrompt, applet_output, user_interaction
from webilastik.features.ilp_filter import IlpFilter

class FeatureSelectionApplet(Applet):
    ilp_feature_names = [
        "GaussianSmoothing",
        "LaplacianOfGaussian",
        "GaussianGradientMagnitude",
        "DifferenceOfGaussians",
        "StructureTensorEigenvalues",
        "HessianOfGaussianEigenvalues",
    ]

    def __init__(self, name: str, *, datasources: AppletOutput[Sequence[DataSource]]):
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

    @user_interaction
    def add_feature_extractors(self, user_prompt: UserPrompt, feature_extractors: Iterable[IlpFilter]) -> PropagationResult:
        return self._set_feature_extractors(
            user_prompt=user_prompt,
            feature_extractors=self._feature_extractors.union(feature_extractors)
        )

    @user_interaction
    def remove_feature_extractors(self, user_prompt: UserPrompt, feature_extractors: Iterable[IlpFilter]) -> PropagationResult:
        return self._set_feature_extractors(
            user_prompt=user_prompt,
            feature_extractors=self._feature_extractors.difference(feature_extractors)
        )

    def on_dependencies_changed(self, user_prompt: UserPrompt) -> PropagationResult:
        return self._set_feature_extractors(user_prompt=user_prompt, feature_extractors=self._feature_extractors)

    @property
    def ilp_data(self) -> Dict[str, Any]:
        feature_extractors = self._feature_extractors
        if len(feature_extractors) == 0:
            return {}

        out: Dict[str, Any] = {"FeatureIds": np.asarray([name.encode("utf8") for name in self.ilp_feature_names])}

        default_scales = [0.3, 0.7, 1.0, 1.6, 3.5, 6.0, 10.0]
        extra_scales = set(fe.ilp_scale for fe in feature_extractors if fe.ilp_scale not in default_scales)
        scales = default_scales + sorted(extra_scales)
        out["Scales"] = np.asarray(scales)

        SelectionMatrix = np.zeros((len(self.ilp_feature_names), len(scales)), dtype=bool)
        for fe in feature_extractors:
            name_idx = self.ilp_feature_names.index(fe.__class__.__name__)
            scale_idx = scales.index(fe.ilp_scale)
            SelectionMatrix[name_idx, scale_idx] = True

        ComputeIn2d = np.full(len(scales), True, dtype=bool)
        for idx, fname in enumerate(self.ilp_feature_names):
            ComputeIn2d[idx] = all(fe.axis_2d for fe in feature_extractors if fe.__class__.__name__ == fname)

        out["SelectionMatrix"] = SelectionMatrix
        out["ComputeIn2d"] = ComputeIn2d  # [: len(scales)]  # weird .ilp quirk in featureTableWidget.py:524
        out["StorageVersion"] = "0.1"
        return out
