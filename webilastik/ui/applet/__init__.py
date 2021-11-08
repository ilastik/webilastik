#pyright: strict

from abc import abstractmethod, ABC
from typing import Any, Callable, Dict, Generic, Iterable, List, Set, Type, TypeVar
from typing_extensions import ParamSpec, Concatenate, final


CONFIRMER = Callable[[str], bool]

def noop_confirmer(msg: str) -> bool:
    return True

class RefreshResult(ABC):
    @abstractmethod
    def _abstract_sentinel(self):
        """Prevents this class from being instantiated"""
        pass

    def is_ok(self) -> bool:
        return isinstance(self, RefreshOk)

class DidNotConfirm(RefreshResult):
    def _abstract_sentinel(self):
        return

class RefreshOk(RefreshResult):
    def _abstract_sentinel(self):
        return


class Applet(ABC):
    def __init__(self, name: str, dependencies: Iterable["AppletOutput[Any]"]) -> None:
        self.name = name

        # touch descriptors to initialize them. FIXME: could this be removed?
        for field_name in vars(self.__class__).keys():
            getattr(self, field_name)

        self.upstream_applets: Set[Applet] = set()
        for dependency in dependencies:
            dependency.subscribe(self)
            self.upstream_applets.add(dependency.applet)
            self.upstream_applets.update(dependency.applet.upstream_applets)

        self.outputs: Dict[str, AppletOutput[Any]] = {}
        for field_name, field in self.__dict__.items():
            if isinstance(field, UserInteraction):
                assert field.applet == self, "Borrowing UserInputs messes up dirty propagation"
            elif isinstance(field, AppletOutput):
                if field.applet == self:
                    self.outputs[field_name] = field

    @abstractmethod
    def take_snapshot(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def restore_snaphot(self, snapshot: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_dependencies_changed(self, confirmer: CONFIRMER) -> RefreshResult:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"

    def get_downstream_applets(self) -> List["Applet"]:
        """Returns a list of the topologically sorted descendants of this applet"""
        out : Set[Applet] = set()
        for output in self.outputs.values():
            out.update(output.get_downstream_applets())
        return sorted(out)

    def __lt__(self, other: "Applet") -> bool:
        return self in other.upstream_applets


APPLET = TypeVar("APPLET", bound="Applet")
P = ParamSpec("P")

class UserInteraction(Generic[P]):
    @classmethod
    def describe(cls, applet_method: Callable[Concatenate[Applet, CONFIRMER, P], RefreshResult]) -> "_UserInteractionDescriptor[P]":
        return _UserInteractionDescriptor[P](applet_method=applet_method)

    # @private
    def __init__(self, *, applet: APPLET, applet_method: Callable[Concatenate[APPLET, CONFIRMER, P], RefreshResult]):
        self.applet = applet
        self._applet_method = applet_method

    def __call__(self, confirmer: CONFIRMER, *args: P.args, **kwargs: P.kwargs) -> RefreshResult:
        applet_snapshots : Dict["Applet", Any] = {}

        def restore_snapshots():
            for applet, snap in applet_snapshots.items():
                applet.restore_snaphot(snap)

        try:
            applet_snapshots[self.applet] = self.applet.take_snapshot()
            action_result = self._applet_method(self.applet, confirmer, *args, **kwargs)
            if not action_result.is_ok():
                restore_snapshots()
                return action_result

            for applet in self.applet.get_downstream_applets():
                applet_snapshots[applet] = applet.take_snapshot()
                refresh_result = applet.on_dependencies_changed(confirmer=confirmer)
                if not refresh_result.is_ok():
                    restore_snapshots()
                    return refresh_result

            return action_result
        except:
            restore_snapshots()
            raise

class _UserInteractionDescriptor(Generic[P]):
    def __init__(self, applet_method: Callable[Concatenate[Applet, CONFIRMER, P], RefreshResult]):
        self._applet_method = applet_method
        self.private_name: str = "__user_interaction_" + applet_method.__name__

    def __get__(self, instance: APPLET, owner: Type[APPLET]) -> "UserInteraction[P]":
        if not hasattr(instance, self.private_name):
            user_input = UserInteraction[P](applet=instance, applet_method=self._applet_method)
            setattr(instance, self.private_name, user_input)
        return getattr(instance, self.private_name)


OUT = TypeVar("OUT", covariant=True)

class AppletOutput(Generic[OUT]):
    @classmethod
    def describe(cls, method: Callable[[Applet], OUT]) -> "_OutputDescriptor[OUT]":
        return _OutputDescriptor(method)

    # private method
    def __init__(self, applet: APPLET, method: Callable[[APPLET], OUT]):
        self._method = method
        self._subscribers: List["Applet"] = []
        self.applet = applet

    def __call__(self) -> OUT:
        return self._method(self.applet)

    def subscribe(self, applet: "Applet"):
        """Registers 'applet' as an observer of this output. Should only be used in Applet's __init__"""
        self._subscribers.append(applet)

    def get_downstream_applets(self) -> List["Applet"]:
        """Returns a list of the topologically sorted applets consuming this output"""
        out : Set["Applet"] = set(self._subscribers)
        for applet in self._subscribers:
            out.update(applet.get_downstream_applets())
        return sorted(out)


class _OutputDescriptor(Generic[OUT]):
    # private method
    def __init__(self, method: Callable[[Applet], OUT]):
        self._method = method
        self.private_name = "__output_slot_" + method.__name__

    def __get__(self, instance: APPLET, owner: Type[APPLET]) -> "AppletOutput[OUT]":
        if not hasattr(instance, self.private_name):
            output_slot = AppletOutput[OUT](applet=instance, method=self._method)
            setattr(instance, self.private_name, output_slot)
        return getattr(instance, self.private_name)


class InertApplet(Applet):
    @final
    def on_dependencies_changed(self, confirmer: CONFIRMER) -> RefreshResult:
        return RefreshOk()


class NoSnapshotApplet(Applet):
    @final
    def take_snapshot(self) -> Any:
        return

    @final
    def restore_snaphot(self, snapshot: Any) -> None:
        return


class StatelesApplet(NoSnapshotApplet, InertApplet):
    pass


class IndependentApplet(InertApplet):
    def __init__(self, name: str) -> None:
        super().__init__(name, dependencies=())
