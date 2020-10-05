from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Generic, TypeVar, Set, Dict, Any
import typing_extensions


class CancelledException(Exception):
    pass


CONFIRMER = Callable[[str], bool]

def noop_confirmer(msg: str) -> bool:
    return True

SV = TypeVar('SV')
class Slot(Generic[SV]):
    def __init__(self, *, owner: "Applet", value: Optional[SV] = None):
        self.owner = owner
        self.subscribers : List["Applet"] = []
        self._value : Optional[SV] = value

    def take_snapshot(self) -> Optional[SV]:
        return self._value

    def restore_snaphot(self, snap: Optional[SV]):
        self._value = snap

    def get_downstream_applets(self) -> List["Applet"]:
        """Returns a list of the topologically sorted applets consuming this slot"""
        out : Set["Applet"] = set(self.subscribers)
        for applet in self.subscribers:
            out.update(applet.get_downstream_applets())
        return sorted(out)

    def subscribe(self, applet: "Applet"):
        self.subscribers.append(applet)

    def refresh(self, confirmer: CONFIRMER):
        pass

    def __call__(self) -> Optional[SV]:
        return self._value

class ValueSlot(Slot[SV]):
    def set_value(self, new_value: Optional[SV], confirmer: CONFIRMER):
        old_value = self._value
        self._value = new_value
        applet_snapshots = {}
        try:
            for applet in [self.owner] + self.owner.get_downstream_applets():
                applet_snapshots[applet] = applet.take_snapshot()
                applet.refresh_derived_slots(confirmer)
        except Exception:
            for applet, snap in applet_snapshots.items():
                applet.restore_snaphot(snap)
            self._value = old_value
            raise

class DerivedSlot(Slot[SV]):
    def __init__(self, owner: "Applet", value_generator: Callable[[CONFIRMER], Optional[SV]]):
        super().__init__(owner=owner)
        self.value_generator = value_generator

    def refresh(self, confirmer: CONFIRMER):
        self._value = self.value_generator(confirmer)


class Applet(ABC):
    def __init__(self):
        self.owned_slots = [
            slot
            for slot in self.__dict__.values()
            if isinstance(slot, Slot) and slot.owner == self
        ]
        self.borrowed_slots = [
            slot
            for slot in self.__dict__.values()
            if isinstance(slot, Slot) and slot.owner != self
        ]
        self.upstream_applets : Set[Applet] = {in_slot.owner for in_slot in self.borrowed_slots}
        for borrowed_slot in self.borrowed_slots:
            self.upstream_applets.update(borrowed_slot.owner.upstream_applets)
            borrowed_slot.subscribe(self)
        self.refresh_derived_slots(confirmer=lambda msg: True)

    def get_downstream_applets(self) -> List["Applet"]:
        """Returns a list of the topologically sorted descendants of this applet"""
        out : Set[Applet] = set()
        for output_slot in self.owned_slots:
            out.update(output_slot.get_downstream_applets())
        return sorted(out)

    def __lt__(self, other: "Applet") -> bool:
        return self in other.upstream_applets

    def take_snapshot(self) -> Dict[Slot, Any]:
        return {slot: slot.take_snapshot() for slot in self.owned_slots}

    def restore_snaphot(self, snap: Dict[Slot, Any]):
        for slot, saved_value in snap.items():
            slot.restore_snaphot(saved_value)

    @typing_extensions.final
    def refresh_derived_slots(self, confirmer: CONFIRMER):
        for slot in self.owned_slots:
            if isinstance(slot, DerivedSlot):
                slot.refresh(confirmer)