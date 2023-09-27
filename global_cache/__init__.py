from typing import Any, Callable, TypeVar
from typing_extensions import ParamSpec
import functools
import os
import sys

P = ParamSpec("P")
T = TypeVar("T", bound=Callable[..., Any])

ENV_VAR_NAME = "LRU_CACHE_MAX_SIZE"
DEFAULT_SIZE = 128
_max_size_env_var = os.environ.get(ENV_VAR_NAME)
if _max_size_env_var is None:
    print(f"{ENV_VAR_NAME} was not set, defaulting to {DEFAULT_SIZE}", file=sys.stderr)
    _maxsize = DEFAULT_SIZE
else:
    print(f"Setting lru_cache maxsize to {_max_size_env_var}", file=sys.stderr)
    _maxsize = int(_max_size_env_var)

def global_cache(func: T) -> T:
    return functools.lru_cache(maxsize=_maxsize)(func) #type: ignore