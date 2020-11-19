from typing import List, TypeVar, Sequence, Optional

from ndstructs.datasource import DataSource

from webilastik.ui.applet import Applet, SequenceProviderApplet, CONFIRMER, Slot, CancelledException
from webilastik.ui.applet.data_selection_applet import ILane
from webilastik.features.ilp_filter import IlpFilter

Lane = TypeVar("Lane", bound=ILane)
class FeatureSelectionApplet(SequenceProviderApplet[IlpFilter]):
    def __init__(self, lanes: Slot[Sequence[Lane]]):
        self._in_lanes = lanes
        super().__init__(refresher=self._refresh_extractors)

    def _refresh_extractors(self, confirmer: CONFIRMER) -> Optional[Sequence[IlpFilter]]:
        current_extractors = list(self.items() or [])
        new_extractors : List[IlpFilter] = []
        current_datasources = [lane.get_raw_data() for lane in self._in_lanes() or []]
        for ex in current_extractors:
            for ds in current_datasources:
                if not ex.is_applicable_to(ds):
                    if confirmer(f"Feature {ex} is not compatible with {ds}. Drop feature extractor?"):
                        break
                    else:
                        raise CancelledException("User did not drop feature extractor")
            else:
                new_extractors.append(ex)
        return tuple(new_extractors)

    def add(self, items: List[IlpFilter], confirmer: CONFIRMER):
        current_datasources = [lane.get_raw_data() for lane in (self._in_lanes() or [])]
        for extractor in items:
            for ds in current_datasources:
                if not extractor.is_applicable_to(ds):
                    raise ValueError(f"Feature Extractor {extractor} is not applicable to datasource {ds}")
        super().add(items, confirmer=confirmer)
