from typing import List, Sequence, TypeVar
from abc import ABC, abstractmethod

from webilastik.ui.applet import Applet, SequenceProviderApplet, Slot, CONFIRMER
from ndstructs.datasource import DataSource

class ILane(ABC):
    @abstractmethod
    def get_raw_data(self) -> DataSource:
        pass

Lane = TypeVar("Lane", bound=ILane)
class DataSelectionApplet(SequenceProviderApplet[Lane]):
    @property
    def lanes(self) -> Slot[Sequence[Lane]]:
        return self.items