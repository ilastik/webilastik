from typing import Any, Callable, TypeVar
from typing_extensions import ParamSpec
import pickle
from functools import wraps
from pathlib import Path
import sys

import redis

from webilastik.utility import get_env_var_or_exit

P = ParamSpec("P")
T = TypeVar("T", bound=Callable[..., Any])

REDIS_UNIX_SOCKET_PATH = get_env_var_or_exit(var_name="REDIS_UNIX_SOCKET_PATH", parser=Path)

if not REDIS_UNIX_SOCKET_PATH.exists():
    print(f"Redis socket path {REDIS_UNIX_SOCKET_PATH} does not exist", file=sys.stderr)
    exit(1)

if not REDIS_UNIX_SOCKET_PATH.is_socket():
    print(f"Redis socket path {REDIS_UNIX_SOCKET_PATH} is not a socket", file=sys.stderr)
    exit(1)

def _redis_cache(func: T) -> T: #FIXME: use Callabe[P, OUT] ?
    @wraps(func)
    def wrapper(*args, **kwargs):
        r = redis.Redis(unix_socket_path=str(REDIS_UNIX_SOCKET_PATH))
        key_tuple = (func.__qualname__, tuple(args), sorted(kwargs.items(), key=lambda x: x[0]))
        key  = pickle.dumps(key_tuple)
        raw_value = r.get(key)
        if raw_value is not None:
            value = pickle.loads(raw_value)
        else:
            value = func(*args, **kwargs)
            _ = r.set(key, pickle.dumps(value))
        return value
    return wrapper #type: ignore

global_cache = _redis_cache