from typing import Generic, Optional, Sequence, TypeVar, Set

from webilastik.datasource import DataSource

from webilastik.annotations.annotation import Annotation
from webilastik.ui.applet import Applet, DerivedSequenceSlot, SequenceValueSlot, CONFIRMER
from webilastik.ui.applet.data_selection_applet import ILane



class BrushingApplet(Applet):
    def __init__(self, name: str):
        self.annotations = SequenceValueSlot[Annotation](owner=self)
        self.datasources = DerivedSequenceSlot[DataSource](owner=self, refresher=self._refresh_datasources)
        super().__init__(name=name)

    def _refresh_datasources(self, confirmer: CONFIRMER) -> Optional[Sequence[DataSource]]:
        datasources : Set[DataSource] = {a.raw_data for a in self.annotations.get() or ()}
        return tuple(datasources) or None
