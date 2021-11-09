# pyright: strict

from typing import Any, Optional
from webilastik.ui.applet import InertApplet, UserCancelled, PropagationOk, PropagationResult, AppletOutput, Applet, NoSnapshotApplet, StatelesApplet, UserInteraction, dummy_prompt, UserPrompt


class InputIdentityApplet(NoSnapshotApplet, InertApplet):
    def __init__(self, name: str) -> None:
        self._value: Optional[int] = None
        super().__init__(name)

    @UserInteraction.describe
    def set_value(self, user_prompt: UserPrompt, value: Optional[int]) -> PropagationResult:
        self._value = value
        return PropagationOk()

    @AppletOutput.describe
    def value(self) -> Optional[int]:
        return self._value


class ForwarderApplet(StatelesApplet):
    def __init__(self, name: str, source: AppletOutput[Optional[int]]) -> None:
        self._source = source
        super().__init__(name)

    @AppletOutput.describe
    def out(self) -> Optional[int]:
        return self._source()


class AdderApplet(StatelesApplet):
    def __init__(self, name: str, source1: AppletOutput[Optional[int]], source2: AppletOutput[Optional[int]]) -> None:
        self._source1 = source1
        self._source2 = source2
        super().__init__(name)

    @AppletOutput.describe
    def out(self) -> Optional[int]:
        val1 = self._source1()
        val2 = self._source2()
        return val1 and (val2 and (val1 + val2))

class PropagationCounterApplet(NoSnapshotApplet):
    def __init__(self, name: str, source: AppletOutput[Optional[int]]) -> None:
        self._source = source
        self.refresh_count = 0
        super().__init__(name)

    def on_dependencies_changed(self, user_prompt: UserPrompt) -> PropagationResult:
        self.refresh_count += 1
        return PropagationOk()

class CachingTripplerApplet(Applet):
    def __init__(self, name: str, source: AppletOutput[Optional[int]]) -> None:
        self._source = source
        self._trippled_cache: Optional[int] = None
        super().__init__(name)

    def take_snapshot(self) -> Any:
        return self._trippled_cache

    def restore_snaphot(self, snapshot: Any):
        self._trippled_cache = snapshot

    def on_dependencies_changed(self, user_prompt: UserPrompt) -> PropagationResult:
        in_value = self._source()
        self._trippled_cache = in_value if in_value is None else in_value * 3
        return PropagationOk()

    @AppletOutput.describe
    def out_trippled(self) -> Optional[int]:
        return self._trippled_cache

class FailingPropagationApplet(NoSnapshotApplet):
    def __init__(self, name: str, fail_after: int, source: AppletOutput[Optional[int]]) -> None:
        self._source = source
        self._fail_after = fail_after
        self._num_refreshes = 0
        super().__init__(name)

    def on_dependencies_changed(self, user_prompt: UserPrompt) -> PropagationResult:
        if self._num_refreshes >= self._fail_after:
            result = UserCancelled()
        else:
            result = PropagationOk()
        self._num_refreshes += 1
        return result

def test_descriptors_produce_independent_slots():
    input_applet_1 = InputIdentityApplet("input1")
    input_applet_2 = InputIdentityApplet("input2")

    assert input_applet_1.value != input_applet_2.value
    assert id(input_applet_1.value) != id(input_applet_2.value)

    assert input_applet_1.set_value != input_applet_2.set_value
    assert id(input_applet_1.set_value) != id(input_applet_2.set_value)

def test_topographic_sorting_of_applets():
    # input -> forwarder_1 -> adder_1 ---> adder_2 -->  forwarder_4 --> adder_3 --> refresh_counter
    # | | |                      ^          ^                            ^
    # | | |                      |          |                            |
    # | | +----> forwarder_2 ----+          |                            |
    # | +-----------------------------------+                            |
    # +------------------------------------------forwarder_3-------------+

    input_applet = InputIdentityApplet("input")
    forwarder_1 = ForwarderApplet("forwarder_1", source=input_applet.value)
    forwarder_2 = ForwarderApplet("forwarder_2", source=input_applet.value)
    forwarder_3 = ForwarderApplet("forwarder_3", source=input_applet.value)

    adder_1 = AdderApplet(name="adder_1", source1=forwarder_1.out, source2=forwarder_2.out)
    adder_2 = AdderApplet(name="adder_1", source1=adder_1.out, source2=input_applet.value)

    forwarder_4 = ForwarderApplet(name="forwarder_4", source=adder_2.out)

    adder_3 = AdderApplet(name="adder_3", source1=forwarder_4.out, source2=forwarder_3.out)

    refresh_counter = PropagationCounterApplet(name="refresh_counter", source = adder_3.out)

    assert len(adder_3.upstream_applets) == 7
    assert adder_3.upstream_applets == set([
        input_applet, forwarder_1, forwarder_2, forwarder_3, adder_1, adder_2, forwarder_4
    ])

    assert len(forwarder_4.upstream_applets) == 5
    assert forwarder_4.upstream_applets == set([
        input_applet, forwarder_1, forwarder_2, adder_1, adder_2
    ])

    assert len(adder_2.upstream_applets) == 4
    assert adder_2.upstream_applets == set([
        input_applet, forwarder_1, forwarder_2, adder_1
    ])

    assert refresh_counter.refresh_count == 0

    result = input_applet.set_value(dummy_prompt, 123)
    assert result.is_ok()
    assert refresh_counter.refresh_count == 1

    result = input_applet.set_value(dummy_prompt, 456)
    assert result.is_ok()
    assert refresh_counter.refresh_count == 2

def test_linear_propagation():
    input_applet = InputIdentityApplet("input")
    forwarder_1 = ForwarderApplet("forwarder 1", source=input_applet.value)
    forwarder_2 = ForwarderApplet("forwarder 2", source=forwarder_1.out)
    forwarder_3 = ForwarderApplet("forwarder 3", source=forwarder_2.out)

    _ = input_applet.set_value(dummy_prompt, 123)
    assert forwarder_3.out() == 123

    _ = input_applet.set_value(dummy_prompt, 456)
    assert forwarder_3.out() == 456


def test_forking_then_joining_applets():
    input_applet = InputIdentityApplet("input")
    forwarder_1 = ForwarderApplet("forwarder 1", source=input_applet.value)
    forwarder_2 = ForwarderApplet("forwarder 2", source=forwarder_1.out)
    adder = AdderApplet("adder", source1=forwarder_1.out, source2=forwarder_2.out)

    _ = input_applet.set_value(dummy_prompt, 123)
    assert adder.out() == 123 + 123

    _ = input_applet.set_value(dummy_prompt, 456)
    assert adder.out() == 456 + 456

def test_refreshing_applet():
    input_applet = InputIdentityApplet("input")
    forwarder_1 = ForwarderApplet("forwarder 1", source=input_applet.value)
    caching_trippler_applet = CachingTripplerApplet(name="caching trippler", source=forwarder_1.out)

    _ = input_applet.set_value(dummy_prompt, 789)
    assert caching_trippler_applet.out_trippled() == 789 * 3

    _ = input_applet.set_value(dummy_prompt, 111)
    assert caching_trippler_applet.out_trippled() == 111 * 3

def test_snapshotting_on_cancelled_refresh():
    input_applet = InputIdentityApplet("input")
    forwarder_1 = ForwarderApplet("forwarder 1", source=input_applet.value)
    caching_trippler_applet = CachingTripplerApplet(name="caching trippler", source=forwarder_1.out)
    _ = FailingPropagationApplet(
        name="failing refresh",
        fail_after=1,
        source=caching_trippler_applet.out_trippled
    )

    result = input_applet.set_value(dummy_prompt, 10)
    assert isinstance(result, PropagationOk)
    assert caching_trippler_applet.out_trippled() == 30

    result = input_applet.set_value(dummy_prompt, 20)
    assert isinstance(result, UserCancelled)
    assert caching_trippler_applet.out_trippled() == 30 # check if value restored back from 60 to 30
