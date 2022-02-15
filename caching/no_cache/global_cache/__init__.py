from typing import Any, Callable, TypeVar
from typing_extensions import ParamSpec

P = ParamSpec("P")
T = TypeVar("T", bound=Callable[..., Any])

def global_cache(func: T) -> T:
    return func