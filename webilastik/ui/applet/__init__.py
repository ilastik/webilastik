#pyright: strict, reportSelfClsParameterName=false



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

class CascadeResult(ABC):
    @abstractmethod
    def _abstract_sentinel(self):
        """Prevents this class from being instantiated"""
        pass

    def is_ok(self) -> bool:
        return isinstance(self, CascadeOk)

class UserCancelled(CascadeResult):
    def _abstract_sentinel(self):
        return

class CascadeOk(CascadeResult):
    def _abstract_sentinel(self):
        return

class CascadeError(CascadeResult):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__()

    def _abstract_sentinel(self):
        return


_propagation_lock = threading.Lock()

class Applet(ABC):
    def __init__(self, name: str) -> None:
        self.name = name
        self.upstream_applets: Set[Applet] = set()
        # FIXME: maybe no __dict__ magic and explicit subscribe?
        for field in self.__dict__.values():
            if isinstance(field, Cascade):
                assert field.applet == self, "Borrowing UserInputs messes up dirty propagation"
            elif isinstance(field, AppletOutput):
                if field.applet is not self:
                    _ = field.subscribe(self) # type: ignore
                    self.upstream_applets.add(field.applet)
                    self.upstream_applets.update(field.applet.upstream_applets)
        super().__init__()

    @abstractmethod
    def take_snapshot(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def restore_snaphot(self, snapshot: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def refresh(self, user_prompt: UserPrompt) -> CascadeResult:
        raise NotImplementedError

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


def cascade(*, refresh_self: bool):
    def wrapper(applet_method: Callable[Concatenate[APPLET, UserPrompt, P], CascadeResult]) -> _CascadeDescriptor[APPLET, P]:
        return _CascadeDescriptor[APPLET, P](refresh_self=refresh_self, applet_method=applet_method)
    return wrapper


class Cascade(Generic[P]):
    # @private
    def __init__(self, *, refresh_self: bool, applet: APPLET, applet_method: Callable[Concatenate[APPLET, UserPrompt, P], CascadeResult]):
        self.refresh_self = refresh_self
        self.applet = applet
        self._applet_method = applet_method
        self.__name__ = applet_method.__name__
        self.__self__ = applet
        super().__init__()

    def __call__(self, user_prompt: UserPrompt, *args: P.args, **kwargs: P.kwargs) -> CascadeResult:
        applet_snapshots : Dict["Applet", Any] = {}

        def restore_snapshots():
            for applet, snap in applet_snapshots.items():
                applet.restore_snaphot(snap)

        try:
            with _propagation_lock:
                applet_snapshots[self.applet] = self.applet.take_snapshot()
                action_result = self._applet_method(self.applet, user_prompt, *args, **kwargs)
                if not action_result.is_ok():
                    restore_snapshots()
                    return action_result

                applets_to_refresh: List[Applet] = [self.applet] if self.refresh_self else []
                applets_to_refresh += self.applet.get_downstream_applets()

                for applet in applets_to_refresh:
                    if applet not in applet_snapshots:
                        applet_snapshots[applet] = applet.take_snapshot()
                    propagation_result = applet.refresh(user_prompt=user_prompt)
                    if not propagation_result.is_ok():
                        restore_snapshots()
                        return propagation_result

                return action_result
        except Exception as e:
            restore_snapshots()
            return CascadeError(str(e))

class _CascadeDescriptor(Generic[APPLET, P]):
    def __init__(self, refresh_self: bool, applet_method: Callable[Concatenate[APPLET, UserPrompt, P], CascadeResult]):
        self.refresh_self = refresh_self
        self._applet_method = applet_method
        self.private_name: str = "__user_interaction_" + applet_method.__name__
        super().__init__()

    def __get__(self, instance: APPLET, owner: Type[APPLET]) -> "Cascade[P]":
        if not hasattr(instance, self.private_name):
            user_input = Cascade[P](refresh_self=self.refresh_self, applet=instance, applet_method=self._applet_method)
            setattr(instance, self.private_name, user_input)
        return getattr(instance, self.private_name)


OUT = TypeVar("OUT", covariant=True)
OUT2 = TypeVar("OUT2", covariant=True)

class AppletOutput(Generic[OUT]):
    """A subscribable method representing the output of an Applet"""

    # private method
    def __init__(
        self,
        applet: APPLET,
        method: Callable[[APPLET], OUT],
        name: Optional[str] = None,
        subscribers: Optional[List[Applet]] = None
    ):
        self._method = method
        self._subscribers: List["Applet"] = subscribers or []
        self.applet = applet
        self.__name__ = name or method.__name__
        self.__self__ = applet
        super().__init__()

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

    def transformed_with(self, transformer: Callable[[OUT], OUT2]) -> "AppletOutput[OUT2]":
        def wrapper(applet: Applet) -> OUT2:
            return transformer(self())
        return AppletOutput(applet=self.applet, method=wrapper, name=self.__name__, subscribers=self._subscribers)


class applet_output(Generic[APPLET, OUT]):
    """A decorator for applet outputs"""

    # private method
    def __init__(self, method: Callable[[APPLET], OUT]):
        self._method = method
        self.private_name = "__output_slot_" + method.__name__
        super().__init__()

    def __get__(self, instance: APPLET, owner: Type[APPLET]) -> "AppletOutput[OUT]":
        if not hasattr(instance, self.private_name):
            output_slot = AppletOutput[OUT](applet=instance, method=self._method)
            setattr(instance, self.private_name, output_slot)
        return getattr(instance, self.private_name)


class InertApplet(Applet):
    @final
    def refresh(self, user_prompt: UserPrompt) -> CascadeResult:
        return CascadeOk()


class NoSnapshotApplet(Applet):
    @final
    def take_snapshot(self) -> Any:
        return

    @final
    def restore_snaphot(self, snapshot: Any) -> None:
        return


class StatelesApplet(NoSnapshotApplet, InertApplet):
    pass
