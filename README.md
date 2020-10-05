"Webilastik" is a rewrite of classic ilastik's architecture to make it more portable and to drop legacy code.

For motivation on the design decisions, have a look at the [presentation](https://docs.google.com/presentation/d/110_1IOqel1QU1aKrznDaZIT5Rr1HbTbUVOfxwVnFFO0/edit)


Webilastik heavily uses [ndstructs](https://github.com/ilastik/ndstructs) to have sane 5D arrays, slices and data sources.

# Server

A PixelClassification workflow can be exposed over http by running `webilastik/server/server.py`. You can make manual requests to the server such as the ones in `webilastik/server/servertest.py` or use [a modified version of Neuroglancer](https://github.com/ilastik/neuroglancer/tree/web_predictions) for that purpose.

The PixelClassificationWorkflow used by the server still doesn't use the experimental `Applets` architecture.

# Concepts


## Operators

A refinement of the Operator concept in classic ilastik; they represent a lazy computation that can be applied to a `ndstructs.datasource.DataSource`.

Operators inherit from the base `Operator` class and must implement `.compute(roi: DataSOurceSlice) -> Array5D`. This means that once you have an operator instantiated, you can apply it over any slice of any `DataSource`.

Operators do *not* deal with Slots or dirty propagation; Those are a UI-only concept in webilastik. Operators are always ready to compute and do not need any other steps to be taken beyond successfully constructing one.

Wherever it makes sense, operators will take a `preprocessor: Optional[Operator]` argument, which allows them to be composed with each other, e.g.:

```python3
thresholder_op = Thresholder(threshold=30)
connected_components_op = ConnectedComponentsExtractor(
    preprocessor=thresholder_op, ...
)
# the connected components operator will first threshold the data with thresholder_op,
# and then look for the components on the thresholded data
# on the thresholded data
connected_components_op.compute(...)
```

## Applets (experimental)

Applets are a UI concept; they usually will represent the user's intent on creating an Operator.

Applets are organized in a Directed Acyclic Graph, where the vertices are the Applets and the edges are `Slots` (see section below).

The base `Applet` class contains some `__init__` logic that **must run after all local slots have been defined**. The easiest way to achieve that is to make sure custom applets call `super().__init__()` as the **last step** of their construction.

### Slots  - applet "live properties" (experimental)

Applets declare their observable properties using a subclass of `Slot`.

Contrary to classic ilastik, there are no `InputSlots` in webilastik, but rather "owned slots" and "borrowed slots". From any applet's perspective:
- "owned slots" are those instantiated inside that same `Applet` (see example below)
- "borrowed slots" are the slots that show up in the constructor signature of an `Applet`, and that therefore belong to some other `Applet`. They are watched for value changes and their values can be used to update the values of the "owned slots" (see example below)

Slots can be either `ValueSlots` or `DerivedSlots`:
- A `ValueSlot` can have its value directly set by `set_value()`. This will cause the owner `Applet` as well as all downstream `Applets` to refresh their `DerivedSlots`
- A `DerivedSlot` must be instantiated with a `value_generator` function, which is responsible for producing the actual value of the slot. This function will be called whenever a `ValueSlot` changes value in the owner `Applet` or in any upstream `Applet`.

| :warning: One should never set a `ValueSlot` inside the `value_generator` function of a `DerivedSlot`! |
| --- |


Whenever an applet (say B) is instantiated by borrowing a slot from another applet (say A), then B is said to be downstream from A, i.e., changes in applet A will trigger a value refresh in the owned `DerivedSlots` of B.

If an exception is raised at any point in the cascading refresh of `DerivedSlots`, the entire `Applet` graph is safely reverted to the previous state.

The `value_generator` argument of `DerivedSlot` is a function that must accept a `confirmer` argument of type `Callable[[str], bool]`. This `confirmer` function should be called by the `value_generator` whenever the applet is about to do something the user might regret (like destroying data or making costly computations). Typical usage would be a GUI passing in a `confirmer` function that shows a "Ok/Cancel" popup. `value_generator` functions should raise a `CancelledException` if the user did not confirm their intent when asked. See the code below for an example of using the `confirmer` function.

Example:

```python3
class ThresholdingApplet(Applet):
    threshold: ValueSlot[float]

    # this applet does not take any slots in its constructor,
    # and therefore has no upstream applets
    def __init__(self, threshold: Optional[float] = None):
        # This is an owned slot, because it was instantiated within this applet.
        # Because it's a ValueSlot, it can be directly set from the
        # outside like so: thresh_op.threshold.set_value(123, ...)
        self.threshold = ValueSlot[float](owner=self, value=threshold)
        super().__init__()  #call Applet.__init__ AFTER all slots have been defined

class ConnectedCompsApplet(Applet):
    number_of_objects: Slot[int]

    # this applet depends on some other applet that provides the 'threshold' Slot
    def __init__(self, threshold: Slot[float]):
        # This is a borrowed slot, because it was created in some other Applet
        # By storing the borrowed threshold slot, this applet is now downstream from
        # the threshold.owner applet
        self._threshold = threshold

        # This DerivedSlot is owned (created in this applet). It automatically refreshes its
        # value whenever the threshold slot changes its value
        self.number_of_objects = DerivedSlot[int](
            owner=self,
            value_generator=self.compute_number_of_objects
        )
        super().__init__() #call Applet.__init__ AFTER all slots have been defined

    # this method is used as the value_generator function of the number_of_objects slot
    # notice that it takes a CONFIRMER function, which is a Callable[[str], bool]. This function is
    # used to ask the user for confirmation before performing slow, costly or destructive operations
    def compute_number_of_objects(self, confirmer: CONFIRMER) -> Optional[int]:
        thresh = self._threshold()
        if thresh is None:
            return None
        if thresh < 10:
            if not confirmer("This will produce a billion objects. Are you sure?"):
                raise CancelledException("User gave up")
        return int(thresh * 1000)
```

These two applets could be combined in a workflow like so:

```python3
# instantiate a thresholding applet
thresh_app = ThresholdingApplet(20)
# instantiate a ConnectedCompsApplet that depends on thresh_app
components_app = ConnectedCompsApplet(threshold=thresh_app.threshold)
# set the threshold directly, probably through a call from the GUI. This
# will cause components_app to also update its values, since it depends
# on the threshold slot from thresh_app
thresh_app.threshold.set_value(1, confirmer=some_gui_confirmation_popup)
```