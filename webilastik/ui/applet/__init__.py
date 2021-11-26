#pyright: strict

from abc import abstractmethod, ABC
import threading
from typing import Any, Callable, Dict, Generic, List, Optional, Protocol, Set, Type, TypeVar
from typing_extensions import ParamSpec, Concatenate, final


T = TypeVar("T")

class UserPrompt(Protocol):
    def __call__(self, message: str, options: Dict[str, T]) -> Optional[T]:
        ...

def dummy_prompt(message: str, options: Dict[str, T]) -> Optional[T]:
    for value in options.values():
        return value
    return None

x: UserPrompt = dummy_prompt

class PropagationResult(ABC):
    @abstractmethod
    def _abstract_sentinel(self):
        """Prevents this class from being instantiated"""
        pass

    def is_ok(self) -> bool:
        return isinstance(self, PropagationOk)

class UserCancelled(PropagationResult):
    def _abstract_sentinel(self):
        return

class PropagationOk(PropagationResult):
    def _abstract_sentinel(self):
        return

class PropagationError(PropagationResult):
    def __init__(self, message: str) -> None:
        self.message = message

    def _abstract_sentinel(self):
        return


_propagation_lock = threading.RLock()

class Applet(ABC):
    def __init__(self, name: str) -> None:
        self.name = name
        self.upstream_applets: Set[Applet] = set()
        for field in self.__dict__.values():
            if isinstance(field, UserInteraction):
                assert field.applet == self, "Borrowing UserInputs messes up dirty propagation"
            elif isinstance(field, AppletOutput):
                if field.applet is not self:
                    _ = field.subscribe(self) # FIXME: maybe no __dict__ magic and explicit subscribe?
                    self.upstream_applets.add(field.applet)
                    self.upstream_applets.update(field.applet.upstream_applets)

    @abstractmethod
    def take_snapshot(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def restore_snaphot(self, snapshot: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_dependencies_changed(self, user_prompt: UserPrompt) -> PropagationResult:
        raise NotImplementedError

    @final
    def propagate_downstream(self, user_prompt: UserPrompt) -> PropagationResult:
        applet_snapshots : Dict["Applet", Any] = {}

        def restore_snapshots():
            for applet, snap in applet_snapshots.items():
                applet.restore_snaphot(snap)

        try:
            with _propagation_lock:
                propagation_result = PropagationOk()
                for applet in self.get_downstream_applets():
                    applet_snapshots[applet] = applet.take_snapshot()
                    propagation_result = applet.on_dependencies_changed(user_prompt=user_prompt)
                    if not propagation_result.is_ok():
                        restore_snapshots()
                        return propagation_result
                return propagation_result
        except:
            restore_snapshots()
            raise

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"

    @final
    def get_downstream_applets(self) -> List["Applet"]:
        """Returns a list of the topologically sorted descendants of this applet"""
        out : Set[Applet] = set()
        for field in self.__dict__.values():
            if isinstance(field, AppletOutput) and field.applet is self:
                out.update(field.get_downstream_applets())
        return sorted(out)

    def __lt__(self, other: "Applet") -> bool:
        return self in other.upstream_applets


APPLET = TypeVar("APPLET", bound="Applet")
P = ParamSpec("P")

class UserInteraction(Generic[P]):
    # @private
    def __init__(self, *, applet: APPLET, applet_method: Callable[Concatenate[APPLET, UserPrompt, P], PropagationResult]):
        self.applet = applet
        self._applet_method = applet_method
        self.__name__ = applet_method.__name__
        self.__self__ = applet

    def __call__(self, user_prompt: UserPrompt, *args: P.args, **kwargs: P.kwargs) -> PropagationResult:
        applet_snapshot = self.applet.take_snapshot()
        try:
            with _propagation_lock:
                action_result = self._applet_method(self.applet, user_prompt, *args, **kwargs)
                if not action_result.is_ok():
                    self.applet.restore_snaphot(applet_snapshot)
                    return action_result
                propagation_result = self.applet.propagate_downstream(user_prompt)
                return action_result if propagation_result.is_ok() else propagation_result
        except:
            self.applet.restore_snaphot(applet_snapshot)
            raise

class user_interaction(Generic[APPLET, P]):
    """A decorator for user interaction methods on applets"""

    def __init__(self, applet_method: Callable[Concatenate[APPLET, UserPrompt, P], PropagationResult]):
        self._applet_method = applet_method
        self.private_name: str = "__user_interaction_" + applet_method.__name__

    def __get__(self, instance: APPLET, owner: Type[APPLET]) -> "UserInteraction[P]":
        if not hasattr(instance, self.private_name):
            user_input = UserInteraction[P](applet=instance, applet_method=self._applet_method)
            setattr(instance, self.private_name, user_input)
        return getattr(instance, self.private_name)


OUT = TypeVar("OUT", covariant=True)

class AppletOutput(Generic[OUT]):
    """A decorator for applet outputs"""

    # private method
    def __init__(self, applet: APPLET, method: Callable[[APPLET], OUT]):
        self._method = method
        self._subscribers: List["Applet"] = []
        self.applet = applet
        self.__name__ = method.__name__
        self.__self__ = applet

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.applet.name}.{self._method.__name__}>"

    def __call__(self) -> OUT:
        return self._method(self.applet)

    def subscribe(self, applet: "Applet") -> "AppletOutput[OUT]":
        """Registers 'applet' as an observer of this output. Should only be used in Applet's __init__"""
        self._subscribers.append(applet)
        return self

    def get_downstream_applets(self) -> List["Applet"]:
        """Returns a list of the topologically sorted applets consuming this output"""
        out : Set["Applet"] = set(self._subscribers)
        for applet in self._subscribers:
            out.add(applet)
            out.update(applet.get_downstream_applets())
        return sorted(out)


class applet_output(Generic[APPLET, OUT]):
    # private method
    def __init__(self, method: Callable[[APPLET], OUT]):
        self._method = method
        self.private_name = "__output_slot_" + method.__name__

    def __get__(self, instance: APPLET, owner: Type[APPLET]) -> "AppletOutput[OUT]":
        if not hasattr(instance, self.private_name):
            output_slot = AppletOutput[OUT](applet=instance, method=self._method)
            setattr(instance, self.private_name, output_slot)
        return getattr(instance, self.private_name)


class InertApplet(Applet):
    @final
    def on_dependencies_changed(self, user_prompt: UserPrompt) -> PropagationResult:
        return PropagationOk()


class NoSnapshotApplet(Applet):
    @final
    def take_snapshot(self) -> Any:
        return

    @final
    def restore_snaphot(self, snapshot: Any) -> None:
        return


class StatelesApplet(NoSnapshotApplet, InertApplet):
    pass
