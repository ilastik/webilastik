from typing import Optional
from webilastik.ui.applet import (
    CONFIRMER, Applet, CancelledException, DerivedSlot, Slot, DerivedSlot, ValueSlot
)


class ThresholdingApplet(Applet):
    threshold: ValueSlot[float]

    def __init__(self, threshold: Optional[float] = None):
        self.threshold = ValueSlot[float](owner=self, value=threshold)
        super().__init__(
            borrowed_slots=[],
            owned_slots=[self.threshold]
        )

class ConnectedCompsApplet(Applet):
    def __init__(self, threshold: Slot[float]):
        self._threshold = threshold
        self.number_of_objects = DerivedSlot[int](
            owner=self,
            value_generator=self.count_number_objects
        )
        super().__init__(
            borrowed_slots=[threshold],
            owned_slots=[self.number_of_objects]
        )

    def count_number_objects(self, confirmer: CONFIRMER) -> Optional[int]:
        thresh = self._threshold()
        if thresh is None:
            return None
        if thresh < 10:
            if not confirmer("This will produce a billion objects. Are you sure?"):
                raise CancelledException("User gave up")
        return int(thresh * 1000)



thresh_app = ThresholdingApplet(20)
components_app = ConnectedCompsApplet(threshold=thresh_app.threshold)
assert components_app.number_of_objects() == 20000

#gui sets some threshold
#this triggers dirty propagation automatically
try:
    thresh_app.threshold.set_value(1, confirmer=lambda msg: False)
except CancelledException as e:
    assert thresh_app.threshold() == 20
    assert components_app.number_of_objects() == 20000

thresh_app.threshold.set_value(1, confirmer=lambda msg: True)
assert thresh_app.threshold() == 1
assert components_app.number_of_objects() == 1000