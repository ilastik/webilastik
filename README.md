"Webilastik" is a rewrite of classic ilastik's architecture to make it more portable and to drop legacy code.

For motivation on the design decisions, have a look at the [presentation](https://docs.google.com/presentation/d/110_1IOqel1QU1aKrznDaZIT5Rr1HbTbUVOfxwVnFFO0/edit?usp=sharing)


Webilastik heavily uses [ndstructs](https://github.com/ilastik/ndstructs) to have sane 5D arrays, slices and data sources.

# Server

In order to use ilastik over the web, a user must first allocate a session (which for now can run either locally as a separate process or remotely on CSCS). This session allocation is done by `webilastik/server/__init__.py` (see `examples/start_manager_for_local_sessions.sh` for an example on how to launch it). This executable is an HTTP handler that will itself spawn other HTTP servers, which are the user sessions, and those sessions will actually run computations for the user.

An HTTP server to expose webilastik should be configured with options analogous to those in `examples/nginx_session_proxy.conf`. The important thing to note is the redirection from requests of the form `session-<session-id>` to `http://unix:/tmp/to-session-$session_id`, since those unix sockets will tunnel back to the user sessions, which might be running in different machines than that which is hosting `webilastik/server/__init__.py`. Also, CORS must be enabled since ilastik will probably not be running on the same server as the viewer.

# Client (Overlay)

This project contains an npm project in `./overlay`, which can be used to build the ilastik client. It is an overlay that can be applied on top of neuroglancer or vanilla HTML `<img/>` tags (for now, via bookmarklet injection), and contains all controls required to request a session, add brush strokes, select image features and visualize predictions.

There is a compiled neuroglancer at `overlay/public/nehuba/index.html` which can be accessed once the session allocation server is running (`webilastik/server/__init__.py`). You can access that and inject ilastik on top of it by first compiling the appropriate target in the overlay project (e.g.: `npm run bundle-ng-inject` or `npm run bundle-img-inject`), then adding the bookmarlets at `overlay/bookmarklets` to your bookmarks toolbar in your browser, and then just executing the bookmark once the page with neuroglancer is loaded.

# Concepts


## Operators

A refinement of the Operator concept in classic ilastik; they represent a lazy computation that usually can be applied to a `ndstructs.datasource.DataRoi`.

Operators inherit from the base `Operator[IN, OUT]` class and must implement `.compute(roi: IN) -> OUT` . The most common implementation being `.compute(roi: DataRoi) -> Array5D` when dealing with operators that use halos. This means that once you have an operator instantiated, you can apply it over any slice of any `DataSource` and the operator will be able to retrieve any extra data if needs from the `DataRoi` object.

Operators do *not* deal with `Slots` or dirty propagation; Those are a UI-only concept in webilastik. Operators are always ready to compute and do not need any other steps to be taken beyond successfully constructing one.

Wherever it makes sense, operators will take a `preprocessor: Optional[Operator]` constructor argument, which allows them to be composed with each other, e.g.:

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

Applets are a UI concept; they usually will represent the user's intent on creating an `Operator`.

Applets are organized in a Directed Acyclic Graph, where the vertices are the Applets and the edges are `Slots` (see section below).

The base `Applet` class contains some `__init__` logic which registers dependencies between applets; This **must run after all local slots have been defined** in the child class constructor. The easiest way to achieve that is to make sure custom applets call `super().__init__()` as the **last step** of their construction. This restriction allows for easy inheritance between custom `Applets` with child classes creating more `Slots`.

Applets are constructed already connected to all of its upstream applets and cannot disconnect from them throughout their lifetimes.

### Slots  - applet "live properties" (experimental)

Applets declare their observable properties using a subclass of `Slot`.

Contrary to classic ilastik, there are no `InputSlots` in webilastik, but rather "owned slots" and "borrowed slots". From any applet's perspective:
- "owned slots" are those instantiated inside that same `Applet` (e.g.: `ValueSlot(owner=self, ...)`. See example below);
- "borrowed slots" are the slots that show up in the constructor signature of an `Applet`, and that therefore belong to some other `Applet`. They are watched for value changes and their values can be used to update the values of the "owned slots" (see example below).

Slots can be either `ValueSlots` or `DerivedSlots`:
- A `ValueSlot` can have its value directly set by `set_value()`. This will cause the owner `Applet` as well as all downstream `Applets` to refresh their slots;
- A `DerivedSlot` must be instantiated with a `refresher` function, which is responsible for producing the actual value of the slot. This function will be called whenever a `ValueSlot` changes value in the owner `Applet` or in any upstream `Applet`.

| :warning: One should never call `ValueSlot.set_value()` inside the `refresher` function of a `Slot`, as that will cause an infinite loop! |
| --- |


Whenever an applet (say B) is instantiated by borrowing a slot from another applet (say A), then B is said to be downstream from A, i.e., changes in applet A will trigger a value refresh in the owned `*Slots` of B; B's `DerivedSlots` will regenerate their values and B's `ValueSlots` will have an opportunity to check if their values are still valid.

If an exception is raised at any point in the cascading refresh of `DerivedSlots`, the entire `Applet` graph is safely reverted to the previous state.

The `refresher` argument of a `Slot` is a function that must accept a `confirmer` argument of type `Callable[[str], bool]`. This `confirmer` function should be called by the `refresher` whenever the applet is about to do something the user might regret (like destroying data or making costly computations). Typical usage would be a GUI passing in a `confirmer` function that shows an "Ok/Cancel" popup. `refresher` functions should raise a `CancelledException` if the user did not confirm their intent when asked. See the code below for an example of using the `confirmer` function.

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
            refresher=self.compute_number_of_objects
        )
        super().__init__() #call Applet.__init__ AFTER all slots have been defined

    # this method is used as the refresher function of the number_of_objects slot
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

## Workflows

Workflows are a predefined collection of `Applets`. Ideally, workflows implement no logic; As much as possible, the `Applets` should be independant of external logic, so that they can be reused in multiple workflows. Interaction with a workflow should also be through the applets, so in a `PixelClassificationWorkflow`, for example, adding brush strokes is done via the `PixelClassificationWorkflow.brushing_applet : BrushingApplet` property, and not through some custom workflow method that would have to be re-implemented for every workflow.
