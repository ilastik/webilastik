from typing import Optional, Sequence, List, Tuple

from ndstructs.datasource import DataSource

from webilastik.annotations.annotation import Annotation
from webilastik.ui.applet import Applet, Slot, SequenceProviderApplet, CONFIRMER, CancelledException
from webilastik.ui.applet.data_selection_applet import ILane



class BrushingApplet(SequenceProviderApplet[Annotation]):
    def __init__(self, lanes: Slot[Sequence[ILane]]):
        self._in_lanes = lanes
        super().__init__(refresher=self._refresh_annotations)

    def _refresh_annotations(self, confirmer: CONFIRMER) -> Optional[Tuple[Annotation]]:
        annotations = self.items() or ()
        present_datasources = {lane.get_raw_data() for lane in self._in_lanes()}
        dangling_annotations = [a for a in annotations if a.raw_data not in present_datasources]
        if dangling_annotations:
            if not confirmer(f"This action will drop these annotations:\n{dangling_annotations}\nContinue?"):
                raise CancelledException("User did not want to drop annotations")
        return tuple(a for a in annotations if a.raw_data in present_datasources)

    def add(self, items: Sequence[Annotation], confirmer: CONFIRMER) -> None:
        current_annotations = self.items() or ()
        current_lanes = self._in_lanes() or ()
        for annotation in items:
            if not any(annotation.raw_data == lane.get_raw_data() for lane in current_lanes):
                raise ValueError(f"Annotation {annotation} references a DataSource not present in any lane")
        super().add(current_annotations + tuple(items), confirmer=confirmer)
