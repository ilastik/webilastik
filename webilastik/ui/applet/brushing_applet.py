from typing import Generic, Optional, Sequence, TypeVar

from ndstructs.datasource import DataSource

from webilastik.annotations.annotation import Annotation
from webilastik.ui.applet import Applet, Slot, ValueSlot, CONFIRMER, CancelledException
from webilastik.ui.applet.data_selection_applet import ILane



LANE = TypeVar("LANE", bound=ILane)
class BrushingApplet(Applet, Generic[LANE]):
    def __init__(self, name: str, *, lanes: Slot[Sequence[LANE]]):
        self._in_lanes = lanes
        self.annotations = ValueSlot[Sequence[Annotation]](owner=self, refresher=self._refresh_annotations)
        super().__init__(name=name)

    def _refresh_annotations(self, confirmer: CONFIRMER) -> Optional[Sequence[Annotation]]:
        annotations = self.annotations.get() or ()
        present_datasources = {lane.get_raw_data() for lane in self._in_lanes.get() or []}
        dangling_annotations = [a for a in annotations if a.raw_data not in present_datasources]
        if dangling_annotations:
            if not confirmer(f"This action will drop these annotations:\n{dangling_annotations}\nContinue?"):
                raise CancelledException("User did not want to drop annotations")
        return tuple(a for a in annotations if a.raw_data in present_datasources) or None
