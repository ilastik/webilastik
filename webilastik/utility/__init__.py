# pyright: reportUnusedImport=false
from traceback import StackSummary
import traceback
from typing import Callable, Generic, Iterable, TypeVar
import threading
import os
import sys

from ndstructs.utils.json_serializable import JsonObject, JsonValue
import datetime

def get_now_string() -> str:
    now = datetime.datetime.now()
    return f"{now.year:02}y{now.month:02}m{now.day:02}d__{now.hour:02}h{now.minute:02}m{now.second:02}s"

T = TypeVar("T")

class Absent:
    pass

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Absent)

    @staticmethod
    def coalesce(value: "T | Absent", default: T) -> T:
        return default if isinstance(value, Absent) else value

    @staticmethod
    def tryGetFromObject(key: str, json_object: JsonObject, parser: Callable[[JsonValue], T]) -> "T | None | Absent":
        if key in json_object:
            value = json_object[key]
            if value is None:
                return value
            return parser(json_object[key])
        return Absent()

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
    default: "T | None" = None,
) -> "T | Exception":
    raw_value = os.environ.get(var_name)
    if raw_value is None:
        if default is not None:
            print(f"Environment variable {var_name} not set. Defaulting to {default}", file=sys.stderr)
            return default
        else:
            return Exception(f"Environment variable {var_name} was not set")

    try:
        return parser(raw_value)
    except Exception as e:
        return e

def get_env_var_or_exit(
    *,
    var_name: str,
    parser: Callable[[str], "T | Exception"],
    default: "T | None" = None,
) -> "T":
    value = get_env_var(var_name=var_name, parser=parser, default=default)
    if isinstance(value, Exception):
        print(f"Environment variable {var_name} not set", file=sys.stderr)
        exit(1)
    return value