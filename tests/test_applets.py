from typing import Optional
from webilastik.ui.applet import (
    CONFIRMER, Applet, CancelledException, DerivedSlot, Slot, DerivedSlot, ValueSlot
)


def test_applet_dirty_propagation():
    class ThresholdingApplet(Applet):
        threshold: ValueSlot[float]

        def __init__(self, threshold: Optional[float] = None):
            self.threshold = ValueSlot[float](owner=self, value=threshold)
            super().__init__()

    class ConnectedCompsApplet(Applet):
        def __init__(self, threshold: Slot[float]):
            self._threshold = threshold
            self.number_of_objects = DerivedSlot[int](
                owner=self,
                value_generator=self.count_number_objects
            )
            super().__init__()

        def count_number_objects(self, confirmer: CONFIRMER) -> Optional[int]:
            thresh = self._threshold()
            if thresh is None:
                return None
            if thresh < 10:
                if not confirmer("This will produce a billion objects. Are you sure?"):
                    raise CancelledException("User gave up")
            return int(thresh * 1000)

    thresh_app = ThresholdingApplet()
    components_app = ConnectedCompsApplet(threshold=thresh_app.threshold)

    thresh_app.threshold.set_value(20, confirmer=lambda msg: True)

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

def test_topologically_sorted_propagate_dirty():
    class IntProvider(Applet):
        def __init__(self):
            self.value_slot = ValueSlot[int](owner=self)
            super().__init__()


    class IntConsumer(Applet):
        def __init__(self, int_input_slot: Slot[int]):
            self.int_input_slot = int_input_slot

            self.str_output = DerivedSlot[str](
                owner=self,
                value_generator=self.generate_output
            )
            super().__init__()

        def generate_output(self, confirmer: CONFIRMER) -> Optional[str]:
            confirmer(self.__class__.__name__)
            return self.__class__.__name__

    class StrAndIntConsumer(IntConsumer):
        def __init__(self, int_input_slot: Slot[int], str_input_slot: Slot[str]):
            self.str_input_slot = str_input_slot
            super().__init__(int_input_slot=int_input_slot)


    called_applet_class_names = []
    def applet_logger(class_name: str) -> bool:
        called_applet_class_names.append(class_name)
        return True

    # provider --int-> int_consumer --str--> str_and_int_consumer
    #    \                                          ^
    #     \                                         |
    #      +-------------------int------------------+

    # whatever order we connect the applets, dirty propagation should still happen
    # in a topologically sorted order, i.e., first provider, then int_consumer, then str_and_int_consumer

    # FIXME: is this test necessary? The fact that applets cannot be instantiated with dangling inputs
    # means that:
    # if B depends on A and C depends on both A and B, then there is no way B won't be instantiated before C,
    # and therefore, B MUST be registered as a downstream applet of A before C gets the chance to register... i think

    provider = IntProvider()
    int_consumer = IntConsumer(int_input_slot=provider.value_slot)
    str_and_int_consumer = StrAndIntConsumer(int_input_slot=provider.value_slot, str_input_slot=int_consumer.str_output)

    provider.value_slot.set_value(123, confirmer=applet_logger)
    assert called_applet_class_names == [IntConsumer.__name__, StrAndIntConsumer.__name__]
