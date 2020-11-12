from typing import Optional, Sequence, List, Set

from ndstructs.datasource import DataSource

from webilastik.annotations.annotation import Annotation
from webilastik.ui.applet import Applet, Slot, SequenceProviderApplet, CONFIRMER, CancelledException
from webilastik.ui.applet.data_selection_applet import ILane



class BrushingApplet(SequenceProviderApplet[Annotation]):
    def __init__(self, lanes: Slot[Sequence[ILane]]):
        self._in_lanes = lanes
        super().__init__(refresher=self._refresh_annotations)

    def _refresh_annotations(self, confirmer: CONFIRMER) -> Optional[Sequence[Annotation]]:
        old_annotations  = set(self.items() or [])
        old_datasources = {a.raw_data for a in old_annotations}
        new_annotations = old_annotations.copy()
        new_datasources = {lane.get_raw_data() for lane in (self._in_lanes() or [])}

        for dropped_ds in old_datasources - new_datasources:
            dangling_annotations = [a for a in old_annotations if a.raw_data == dropped_ds]
            if not confirmer(f"Removing datasource {dropped_ds} will drop these annotations:\n{dangling_annotations}\nContinue?"):
                raise CancelledException("User did not want to drop annotations")
            new_annotations.difference_update(dangling_annotations)

        return list(new_annotations)

    def add(self, items: List[Annotation], confirmer: CONFIRMER) -> None:
        current_annotations = self.items() or []
        current_lanes = self._in_lanes() or []
        for annotation in items:
            if not any(annotation.raw_data == lane.get_raw_data() for lane in current_lanes):
                raise ValueError(f"Annotation {annotation} references a DataSource not present in any lane")
        super().add(current_annotations + items, confirmer=confirmer)
