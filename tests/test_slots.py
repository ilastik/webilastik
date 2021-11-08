# pyright: strict

from typing import Any, Optional
from webilastik.ui.applet import RefreshOk, RefreshResult, Output, Applet, StatelessApplet, UserInteraction, noop_confirmer, CONFIRMER


class InputIdentityApplet(StatelessApplet):
    def __init__(self, name: str) -> None:
        self._value: Optional[int] = None
        super().__init__(name)

    @UserInteraction.describe
    def set_value(self, confirmer: CONFIRMER, value: Optional[int]) -> RefreshResult:
        self._value = value
        return RefreshOk()

    @Output.describe
    def value(self) -> Optional[int]:
        return self._value


class SingleInSingleOutApplet(StatelessApplet):
    def __init__(self, name: str, value: Output[Optional[int]]) -> None:
        self._value_source = value
        super().__init__(name)

    @Output.describe
    def out(self) -> Optional[int]:
        return self._value_source()


class CachingTripplerApplet(Applet):
    def __init__(self, name: str, value: Output[Optional[int]]) -> None:
        self._value_source = value
        self._trippled_cache: Optional[int] = None
        super().__init__(name)

    def take_snapshot(self) -> Any:
        return self._trippled_cache

    def restore_snaphot(self, snapshot: Any):
        self._trippled_cache = snapshot

    def on_dependencies_changed(self, confirmer: CONFIRMER) -> RefreshResult:
        in_value = self._value_source()
        self._trippled_cache = in_value if in_value is None else in_value * 3
        return RefreshOk()

    @Output.describe
    def trippled(self) -> Optional[int]:
        return self._trippled_cache

class MultiInputRefreshingApplet(Applet):
    def __init__(
        self,
        *,
        name: str,
        value1: Output[Optional[int]],
        value2: Output[Optional[int]],
    ) -> None:
        self._value_source1 = value1
        self._value_source2 = value2
        self.refresh_count = 0
        super().__init__(name)

    def take_snapshot(self) -> Any:
        return

    def restore_snaphot(self, snapshot: Any):
        return

    def on_dependencies_changed(self, confirmer: CONFIRMER) -> RefreshResult:
        self.refresh_count += 1
        return RefreshOk()

class MultiDependencyApplet(StatelessApplet):
    def __init__(self, name: str, value1: Output[Optional[int]], value2: Output[Optional[int]]) -> None:
        self._value_source1 = value1
        self._value_source2 = value2
        super().__init__(name)

    @Output.describe
    def inputs_sum(self) -> Optional[int]:
        val1 = self._value_source1()
        val2 = self._value_source2()
        return val1 and (val2 and (val1 + val2))

def test_descriptors_produce_independent_slots():
    input_applet_1 = InputIdentityApplet("input1")
    input_applet_2 = InputIdentityApplet("input2")

    assert input_applet_1.value != input_applet_2.value
    assert id(input_applet_1.value) != id(input_applet_2.value)

    assert input_applet_1.set_value != input_applet_2.set_value
    assert id(input_applet_1.set_value) != id(input_applet_2.set_value)

def test_linear_propagation():
    input_applet = InputIdentityApplet("input")
    single_in_single_out_1 = SingleInSingleOutApplet("single in, single out 1", value=input_applet.value)
    single_in_single_out_2 = SingleInSingleOutApplet("single in, single out 2", value=single_in_single_out_1.out)
    single_in_single_out_3 = SingleInSingleOutApplet("single in, single out 3", value=single_in_single_out_2.out)

    _ = input_applet.set_value(noop_confirmer, 123)
    assert single_in_single_out_3.out() == 123

    _ = input_applet.set_value(noop_confirmer, 456)
    assert single_in_single_out_3.out() == 456


def test_forking_then_joining_applets():
    input_applet = InputIdentityApplet("input")
    single_in_single_out_1 = SingleInSingleOutApplet("single in, single out 1", value=input_applet.value)
    single_in_single_out_2 = SingleInSingleOutApplet("single in, single out 2", value=single_in_single_out_1.out)
    multi_dep_applet = MultiDependencyApplet("multi_dep_applet", value1=single_in_single_out_1.out, value2=single_in_single_out_2.out)

    _ = input_applet.set_value(noop_confirmer, 123)
    assert multi_dep_applet.inputs_sum() == 123 + 123

    _ = input_applet.set_value(noop_confirmer, 456)
    assert multi_dep_applet.inputs_sum() == 456 + 456

def test_refreshing_applet():
    input_applet = InputIdentityApplet("input")
    single_in_single_out_1 = SingleInSingleOutApplet("single in, single out 1", value=input_applet.value)
    caching_trippler_applet = CachingTripplerApplet(name="caching trippler", value=single_in_single_out_1.out)

    _ = input_applet.set_value(noop_confirmer, 789)
    assert caching_trippler_applet.trippled() == 789 * 3

    _ = input_applet.set_value(noop_confirmer, 111)
    assert caching_trippler_applet.trippled() == 111 * 3

def test_refresh_doesnt_trigger_twice():
    # updating 'input_applet' should refresh multi_input_refreshing_applet only once
    #
    # input_applet -> single_in_single_out_1 --> multi_input_refreshing_applet
    #  \                                         ^
    #   \                                        |
    #    +-> single_in_single_out_2 -------------+

    input_applet = InputIdentityApplet("input")
    single_in_single_out_1 = SingleInSingleOutApplet("single in, single out 1", value=input_applet.value)
    single_in_single_out_2 = SingleInSingleOutApplet("single in, single out 2", value=input_applet.value)
    multi_input_refreshing_applet1 = MultiInputRefreshingApplet(
        name="caching trippler",
        value1=single_in_single_out_1.out,
        value2=single_in_single_out_2.out,
    )

    _ = input_applet.set_value(noop_confirmer, 789)
    assert multi_input_refreshing_applet1.refresh_count == 1

    multi_input_refreshing_applet2 = MultiInputRefreshingApplet(
        name="caching trippler 2",
        value1=single_in_single_out_2.out,
        value2=single_in_single_out_1.out,
    )

    _ = input_applet.set_value(noop_confirmer, 111)
    assert multi_input_refreshing_applet1.refresh_count == 2
    assert multi_input_refreshing_applet2.refresh_count == 1
