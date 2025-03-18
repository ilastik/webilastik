from typing import Any, Callable, Tuple, TypeVar
from typing_extensions import ParamSpec
import pickle
from functools import wraps
from pathlib import Path
import sys
import os

import redis # pyright: ignore [reportMissingTypeStubs]

from webilastik.utility import get_env_var_or_exit

P = ParamSpec("P")
T = TypeVar("T", bound=Callable[..., Any])

def parse_ip_port(value: str) -> Tuple[str, int]:
    ip_str, port = value.split(":")
    return ip_str, int(port)

REDIS_HOST_PORT = os.environ.get("REDIS_HOST_PORT")
if REDIS_HOST_PORT is not None:
    redis_host, port_str = REDIS_HOST_PORT.split(":")
    redis_factory = lambda: redis.Redis(host=redis_host, port=int(port_str))
else:
    REDIS_UNIX_SOCKET_PATH = get_env_var_or_exit(var_name="REDIS_UNIX_SOCKET_PATH", parser=Path)
    if not REDIS_UNIX_SOCKET_PATH.exists():
        print(f"Redis socket path {REDIS_UNIX_SOCKET_PATH} does not exist", file=sys.stderr)
        exit(1)
    if not REDIS_UNIX_SOCKET_PATH.is_socket():
        print(f"Redis socket path {REDIS_UNIX_SOCKET_PATH} is not a socket", file=sys.stderr)
        exit(1)
    redis_factory = lambda: redis.Redis(unix_socket_path=str(REDIS_UNIX_SOCKET_PATH))

def _redis_cache(func: T) -> T: #FIXME: use Callabe[P, OUT] ?
    @wraps(func)
    def wrapper(*args, **kwargs):
        r = redis_factory()
        key_tuple = (func.__qualname__, tuple(args), sorted(kwargs.items(), key=lambda x: x[0]))
        key  = pickle.dumps(key_tuple)
        raw_value = r.get(key)
        if raw_value is not None:
            value = pickle.loads(raw_value) # pyright: ignore [reportArgumentType]
        else:
            value = func(*args, **kwargs)
            _ = r.set(key, pickle.dumps(value))
        return value
    return wrapper #type: ignore

global_cache = _redis_cache
