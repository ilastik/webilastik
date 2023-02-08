from typing import Any, Callable, TypeVar
from typing_extensions import ParamSpec, assert_never
import pickle
from functools import wraps

import redis
from webilastik.config import RedisCacheConfig, REDIS_CACHE_UNIX_SOCKET_PATH, RedisCacheTcpConfig

from webilastik.utility import eprint

T = TypeVar("T", bound=Callable[..., Any])

_redis_config_result = RedisCacheConfig.try_get()
if isinstance(_redis_config_result, Exception):
    eprint(f"Error getting redis configuration: {_redis_config_result}")
    exit(1)
if isinstance(_redis_config_result, type(None)):
    eprint(f"Missing redis configuration")
    exit(1)

if isinstance(_redis_config_result.config, REDIS_CACHE_UNIX_SOCKET_PATH):
    socket_path = _redis_config_result.config.value
    redis_factory = lambda: redis.Redis(unix_socket_path=str(socket_path))
elif isinstance(_redis_config_result.config, RedisCacheTcpConfig):
    redis_host_str = str(_redis_config_result.config.ip.value)
    redis_port = _redis_config_result.config.port.value
    redis_factory = lambda: redis.Redis(host=redis_host_str, port=redis_port)
else:
    assert_never(_redis_config_result.config)


def _redis_cache(func: T) -> T: #FIXME: use Callabe[P, OUT] ?
    @wraps(func)
    def wrapper(*args, **kwargs):
        r = redis_factory()
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