from abc import ABC
from typing import List, Sequence, Optional, Callable, Generic, TypeVar, Set, Dict, Any, Tuple, Union
import typing_extensions


class CancelledException(Exception):
    pass

class NotReadyException(Exception):
    pass

CONFIRMER = Callable[[str], bool]

def noop_confirmer(msg: str) -> bool:
    return True

SV = TypeVar('SV')
SLOT_REFRESHER=Callable[[CONFIRMER], Optional[SV]]
class Slot(Generic[SV], ABC):
    """A watchable/dynamic property of an Applet. "Private" methods are meant to be used either by the
    *Slot classes or by the base Applet class, as they must work in tandem to propagate value changes"""
    def __init__(
        self,
        *,
        owner: "Applet",
        value: Optional[SV] = None,
        refresher: Optional[SLOT_REFRESHER[SV]]=None,
    ):
        self._owner = owner
        self._refresher = refresher
        self._subscribers : List["Applet"] = []
        self._value : Optional[SV] = value

    def __repr__(self) -> str:
        for field_name, field_value in self._owner.__dict__.items():
            if field_value == self:
                return f"<Slot {self._owner}.{field_name}>"
        raise Exception("Could not find self in {self.owner}")

    def _take_snapshot(self) -> Optional[SV]:
        return self._value

    def _restore_snaphot(self, snap: Optional[SV]):
        self._value = snap

    def get_downstream_applets(self) -> List["Applet"]:
        """Returns a list of the topologically sorted applets consuming this slot"""
        out : Set["Applet"] = set(self._subscribers)
        for applet in self._subscribers:
            out.update(applet.get_downstream_applets())
        return sorted(out)

    def _subscribe(self, applet: "Applet"):
        self._subscribers.append(applet)

    def _refresh(self, confirmer: CONFIRMER):
        if self._refresher is not None:
            try:
                self._value = self._refresher(confirmer)
            except NotReadyException:
                self._value = None

    def __call__(self) -> SV: #raises NotReadyException
        if self._value is None:
            raise NotReadyException()
        return self._value

    def get(self, default: Optional[SV] = None) -> Optional[SV]:
        return self._value


class DerivedSlot(Slot[SV]):
    """DerivedSlots cannot have their values directly set; They only update as a consequence of value changes in
    slots in the same applet on in any upstream aplet, which will cause the refresher function to be called"""

    def __init__(self, owner: "Applet", refresher: SLOT_REFRESHER[SV]):
        super().__init__(owner=owner, refresher=refresher)

class ValueSlot(Slot[SV]):
    """ValueSlots can be set by human users by calling set_value (or having the GUI do it for them).
    This slot can still use a refresher function like in DeriveSlot which can be used to validate if
    a user input is still valid given the latest change in the values of the other Slots, and to adjust
    such value if need be."""

    def set_value(self, new_value: Optional[SV], confirmer: CONFIRMER):
        old_value = self._value
        self._value = new_value
        applet_snapshots : Dict["Applet", Any] = {}
        try:
            for applet in [self._owner] + self._owner.get_downstream_applets():
                applet_snapshots[applet] = applet.take_snapshot()
                applet.refresh_derived_slots(confirmer=confirmer, provoker=self)
        except Exception:
            for applet, snap in applet_snapshots.items():
                applet.restore_snaphot(snap)
            self._value = old_value
            raise


class Applet(ABC):
    """Applets are the base of the user interface, and human users can interact directly with them, calling public
    methods and setting values of ValueSlots, which will trigger updates on other slots in downstream applets"""
    def __init__(self, name: str):
        self.name = name
        self.owned_slots = {
            slot_name: slot
            for slot_name, slot in self.__dict__.items()
            if isinstance(slot, Slot) and slot._owner == self
        }
        self.borrowed_slots = {
            slot_name: slot
            for slot_name, slot in self.__dict__.items()
            if isinstance(slot, Slot) and slot._owner != self
        }
        self.upstream_applets : Set[Applet] = {in_slot._owner for in_slot in self.borrowed_slots.values()}
        for borrowed_slot in self.borrowed_slots.values():
            self.upstream_applets.update(borrowed_slot._owner.upstream_applets)
            borrowed_slot._subscribe(self)

    def get_downstream_applets(self) -> List["Applet"]:
        """Returns a list of the topologically sorted descendants of this applet"""
        out : Set[Applet] = set()
        for output_slot in self.owned_slots.values():
            out.update(output_slot.get_downstream_applets())
        return sorted(out)

    def __lt__(self, other: "Applet") -> bool:
        return self in other.upstream_applets

    def take_snapshot(self) -> Dict[str, Any]:
        return {slot_name: slot._take_snapshot() for slot_name, slot in self.owned_slots.items()}

    def restore_snaphot(self, snap: Dict[str, Any]):
        for slot_name, saved_value in snap.items():
            slot = self.owned_slots[slot_name]
            slot._restore_snaphot(saved_value)

    @typing_extensions.final
    def refresh_derived_slots(self, confirmer: CONFIRMER, provoker: Slot[Any]):
        self.pre_refresh(confirmer)
        for slot in self.owned_slots.values():
            if slot != provoker:
                slot._refresh(confirmer)
        self.post_refresh(confirmer)

    def pre_refresh(self, confirmer: CONFIRMER):
        pass

    def post_refresh(self, confirmer: CONFIRMER):
        pass
