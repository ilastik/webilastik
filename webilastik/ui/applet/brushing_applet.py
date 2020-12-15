from typing import Generic, Optional, Sequence, TypeVar

from ndstructs.datasource import DataSource

from webilastik.annotations.annotation import Annotation
from webilastik.ui.applet import Slot, CONFIRMER, CancelledException
from webilastik.ui.applet.sequence_provider_applet import SequenceProviderApplet
from webilastik.ui.applet.data_selection_applet import ILane



LANE = TypeVar("LANE", bound=ILane)
class BrushingApplet(SequenceProviderApplet[Annotation], Generic[LANE]):
    def __init__(self, name: str, *, lanes: Slot[Sequence[LANE]]):
        self._in_lanes = lanes
        super().__init__(name=name, refresher=self._refresh_annotations)

    def _refresh_annotations(self, confirmer: CONFIRMER) -> Optional[Sequence[Annotation]]:
        annotations = self.items.get() or ()
        present_datasources = {lane.get_raw_data() for lane in self._in_lanes.get() or []}
        dangling_annotations = [a for a in annotations if a.raw_data not in present_datasources]
        if dangling_annotations:
            if not confirmer(f"This action will drop these annotations:\n{dangling_annotations}\nContinue?"):
                raise CancelledException("User did not want to drop annotations")
        return tuple(a for a in annotations if a.raw_data in present_datasources) or None

    def add(self, items: Sequence[Annotation], confirmer: CONFIRMER) -> None:
        current_lanes = self._in_lanes.get() or ()
        for annotation in items:
            if not any(annotation.raw_data == lane.get_raw_data() for lane in current_lanes):
                raise ValueError(f"Annotation {annotation} references a DataSource not present in any lane")
        super().add(items, confirmer=confirmer)
