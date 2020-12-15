from typing import List, TypeVar, Sequence, Optional, Dict, Any, Iterator

import numpy as np

from webilastik.ui.applet import Applet, CONFIRMER, Slot, CancelledException
from webilastik.ui.applet.sequence_provider_applet import SequenceProviderApplet
from webilastik.ui.applet.data_selection_applet import ILane
from webilastik.features.ilp_filter import IlpFilter

LANE = TypeVar("LANE", bound=ILane)
class FeatureSelectionApplet(SequenceProviderApplet[IlpFilter]):
    ilp_feature_names = [
        "GaussianSmoothing",
        "LaplacianOfGaussian",
        "GaussianGradientMagnitude",
        "DifferenceOfGaussians",
        "StructureTensorEigenvalues",
        "HessianOfGaussianEigenvalues",
    ]


    def __init__(self, name: str, *, lanes: Slot[Sequence[LANE]]):
        self._in_lanes = lanes
        super().__init__(name=name, refresher=self._refresh_extractors)

    def _refresh_extractors(self, confirmer: CONFIRMER) -> Optional[Sequence[IlpFilter]]:
        current_extractors = list(self.items.get() or ())
        new_extractors : List[IlpFilter] = []
        current_datasources = [lane.get_raw_data() for lane in self._in_lanes.get() or ()]
        for ex in current_extractors:
            for ds in current_datasources:
                if not ex.is_applicable_to(ds):
                    if confirmer(f"Feature {ex} is not compatible with {ds}. Drop feature extractor?"):
                        break
                    else:
                        raise CancelledException("User did not drop feature extractor")
            else:
                new_extractors.append(ex)
        return tuple(new_extractors) or None

    def add(self, items: Sequence[IlpFilter], confirmer: CONFIRMER):
        current_datasources = [lane.get_raw_data() for lane in self._in_lanes.get() or ()]
        for extractor in items:
            for ds in current_datasources:
                if not extractor.is_applicable_to(ds):
                    raise ValueError(f"Feature Extractor {extractor} is not applicable to datasource {ds}")
        super().add(items, confirmer=confirmer)

    @property
    def ilp_data(self) -> Dict[str, Any]:
        feature_extractors = self.items.get()
        if not feature_extractors:
            return {}

        out = {"FeatureIds": np.asarray([name.encode("utf8") for name in self.ilp_feature_names])}

        default_scales = [0.3, 0.7, 1.0, 1.6, 3.5, 6.0, 10.0] #FIXME allow arbitrary scales
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
