from typing import TypeVar, Generic, Sequence, Optional

from webilastik.ui.applet import CONFIRMER, SLOT_REFRESHER, Applet, ValueSlot

Item_co = TypeVar("Item_co", covariant=True)
class SequenceProviderApplet(Applet, Generic[Item_co]):
    """A simple applet managing a Sequence of elements"""

    def __init__(self, name: str, refresher: Optional[ SLOT_REFRESHER[Sequence[Item_co]]  ]=None):
        self.items = ValueSlot[Sequence[Item_co]](owner=self, refresher=refresher)
        super().__init__(name=name)

    def _set_items(self, items: Sequence[Item_co], confirmer: CONFIRMER):
        self.items.set_value(tuple(items) if len(items) > 0 else None, confirmer=confirmer)

    def add(self, items: Sequence[Item_co], confirmer: CONFIRMER) -> None:
        current_items = tuple(self.items.get() or ())
        for item in items:
            if item in current_items:
                raise ValueError(f"{item.__class__.__name__} {item} has already been added")
        self._set_items(current_items + tuple(items), confirmer=confirmer)

    def remove_at(self, idx: int, confirmer: CONFIRMER) -> None:
        items = list(self.items())
        items.pop(idx)
        self._set_items(items, confirmer=confirmer)

    def remove(self, items: Sequence[Item_co], confirmer: CONFIRMER) -> None:
        new_items = tuple(item for item in self.items() if item not in items)
        self._set_items(new_items, confirmer=confirmer)

    def clear(self, confirmer: CONFIRMER) -> None:
        self._set_items((), confirmer=confirmer)
