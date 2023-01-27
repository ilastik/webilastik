# pyright: reportUnusedImport=false
from traceback import StackSummary
import traceback
from typing import Callable, Generic, Iterable, Literal, Mapping, NewType, TypeVar
import threading
import os
import sys
from typing_extensions import Protocol, Self

from ndstructs.utils.json_serializable import JsonObject, JsonValue
import datetime

LogLevel = Literal["error", "warning", "info", "debug", "normal"]

COLOR_ESCAPE: Mapping[LogLevel, str] = {
    "error": "\033[31m",
    "warning": "\033[33m",
    "info": "\033[0m",
    "debug": "\033[38;5;145m",
    "normal": "\033[0m",
}

def eprint(message: str, level: Literal["error", "warning", "info", "debug"] = "info"):
    if not sys.stderr.isatty():
        print(message, file=sys.stderr)
    print(COLOR_ESCAPE[level], message, COLOR_ESCAPE["normal"])

def get_now_string() -> str:
    now = datetime.datetime.now()
    return f"{now.year:02}y{now.month:02}m{now.day:02}d__{now.hour:02}h{now.minute:02}m{now.second:02}s"

T = TypeVar("T")

A = TypeVar("A", covariant=True)

class _Empty:
    pass

class PeekableIterator(Generic[A]):
    def __init__(self, args: Iterable[A]) -> None:
        self.args = iter(args)
        self.next_arg: "A | _Empty" = _Empty()
        try:
            self.next_arg = next(self.args)
        except StopIteration:
            pass
        super().__init__()

    def has_next(self) -> bool:
        return not isinstance(self.next_arg, _Empty)

    def get_next(self) -> "A":
        if isinstance(self.next_arg, _Empty):
            raise ValueError(f"Iterator is empty")
        out = self.next_arg
        try:
            self.next_arg = next(self.args)
        except StopIteration:
            self.next_arg = _Empty()
        return out

class DebugLock:
    def __init__(self, timeout: int = 15) -> None:
        self._lock = threading.Lock()
        self.timeout = timeout
        self.traceback: "StackSummary | None" = None
        super().__init__()

    def __enter__(self, *args, **kwargs) -> "DebugLock":
        got_it = self._lock.acquire(timeout=self.timeout)
        if not got_it:
            RED="\033[31m"
            END="\033[0m"

            assert self.traceback is not None
            print(
                f"{RED}!!!!!Could not acquire lock at{END}" + "\n" +
                "".join(traceback.format_list(traceback.extract_stack())) +
                f"{RED}because it's acquired by{END}" + "\n" +
                "".join(traceback.format_list(self.traceback))
            )
        self.traceback = traceback.extract_stack()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.traceback = None
        self._lock.release()



def get_env_var(
    *,
    var_name: str,
    parser: Callable[[str], "T | Exception"],
    default: "T | _Empty" = _Empty(),
) -> "T | Exception":
    raw_value = os.environ.get(var_name)
    if raw_value is None:
        if isinstance(default, _Empty):
            return Exception(f"Environment variable {var_name} was not set")
        else:
            print(f"Environment variable {var_name} not set. Defaulting to {default}", file=sys.stderr)
            return default

    try:
        return parser(raw_value)
    except Exception as e:
        return e

def get_env_var_or_exit(
    *,
    var_name: str,
    parser: Callable[[str], "T | Exception"],
    default: "T | _Empty" = _Empty(),
) -> "T":
    value = get_env_var(var_name=var_name, parser=parser, default=default)
    if isinstance(value, Exception):
        print(f"Environment variable {var_name} not set", file=sys.stderr)
        exit(1)
    return value


Username = NewType("Username", str)
Hostname = NewType("Hostname", str)

class NewTypeNumber:
    def __init__(self, value: float) -> None:
        super().__init__()
        self._value = value

    def __add__(self, other: Self) -> Self:
        return self.__class__(self._value + other._value)

    def __sub__(self, other: Self) -> Self:
        return self.__class__(self._value - other._value)

    def __gt__(self, other: Self) -> bool:
        return self._value > other._value

    def __lt__(self, other: Self) -> bool:
        return self._value < other._value

    def __eq__(self, o: object) -> bool:
        return isinstance(o, self.__class__) and self._value == o._value

    def __str__(self) -> str:
        return str(self._value)

    def to_float(self) -> float:
        return self._value

    def to_int(self) -> int:
        return int(self._value)

    @classmethod
    def try_from_str(cls, value: str) -> "Self | ValueError":
        try:
            return cls(float(value))
        except ValueError as e:
            return e

class Minutes(NewTypeNumber):
    def to_seconds(self) -> "Seconds":
        return Seconds(self._value * 60)

    def __mul__(self, nodes: "ComputeNodes") -> "NodeMinutes":
        return NodeMinutes(self._value * nodes._value)

class Seconds(NewTypeNumber):
    def __mul__(self, other: "ComputeNodes") -> "NodeSeconds":
        return NodeSeconds(self._value * other._value)

class ComputeNodes(NewTypeNumber):
    def __mul__(self, other: "Seconds") -> "NodeSeconds":
        return NodeSeconds(self._value * other._value)

class NodeSeconds(NewTypeNumber):
    def to_node_minutes(self) -> "NodeMinutes":
        return NodeMinutes(self._value / 60)

    def to_node_hours(self) -> "NodeHours":
        return NodeHours(self._value / 3600)

class NodeMinutes(NewTypeNumber):
    pass

class NodeHours(NewTypeNumber):
    def to_node_seconds(self) -> "NodeSeconds":
        return NodeSeconds(self._value * 3600)

    def to_node_minutes(self) -> "NodeMinutes":
        return NodeMinutes(self._value * 60)

class Nanometers(NewTypeNumber):
    pass

class Nanoseconds(NewTypeNumber):
    pass