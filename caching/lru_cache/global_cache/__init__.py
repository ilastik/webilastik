from typing import Any, Callable, TypeVar
from typing_extensions import ParamSpec
import functools
import os
import sys

from webilastik.config import WEBILASTIK_LRU_CACHE_MAX_SIZE
from webilastik.utility import eprint

P = ParamSpec("P")
T = TypeVar("T", bound=Callable[..., Any])

_cache_size_config = WEBILASTIK_LRU_CACHE_MAX_SIZE.try_get()
if isinstance(_cache_size_config, Exception):
    eprint(f"Bad configuration: {_cache_size_config}")
    exit(1)
if _cache_size_config is None:
   _cache_size: int = 128
else:
    _cache_size: int = _cache_size_config.value

def global_cache(func: T) -> T:
    return functools.lru_cache(maxsize=_cache_size)(func) #type: ignore