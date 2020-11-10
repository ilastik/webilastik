from typing import List

from ndstructs.datasource import DataSource

from webilastik.ui.applet import Applet, ValueSlot, CONFIRMER, Slot
from webilastik.features.ilp_filter import IlpFilter

class FeatureSelectionApplet(Applet):
    def __init__(self, datasources: Slot[List[DataSource]]):
        self.in_datasources = datasources
        self.feature_extractors = ValueSlot[List[IlpFilter]](owner=self)
        super().__init__()

    def clear_feature_extractors(self, *, confirmer: CONFIRMER) -> None:
        self.feature_extractors.set_value(None, confirmer=confirmer)

    def add_feature_extractors(self, extractors: List[IlpFilter], confirmer: CONFIRMER):
        current_extractors = self.feature_extractors() or []
        current_datasources = self.in_datasources() or []
        for extractor in extractors:
            if extractor in current_extractors:
                raise ValueError(f"Feature Extractor {extractor} is already present in this Workflow")
            for ds in current_datasources:
                if not extractor.is_applicable_to(ds):
                    raise ValueError(f"Feature Extractor {extractor} is not applicable to datasource {ds}")
        self.feature_extractors.set_value(current_extractors + extractors, confirmer=confirmer)
