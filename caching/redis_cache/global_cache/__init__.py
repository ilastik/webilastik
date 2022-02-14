from typing import Any, Callable, TypeVar
from typing_extensions import ParamSpec
import pickle
from functools import wraps

import redis

P = ParamSpec("P")
T = TypeVar("T", bound=Callable[..., Any])

redis_pool = redis.BlockingConnectionPool()

def _redis_cache(func: T) -> T:
    @wraps(func)
    def wrapper(*args, **kwargs):
        r = redis.Redis(connection_pool=redis_pool)
        key_tuple = (func.__qualname__, tuple(args), sorted(kwargs.items(), key=lambda x: x[0])),
        key  = pickle.dumps(key_tuple)
        raw_value = r.get(key)
        if raw_value is not None:
            value = pickle.loads(raw_value)
        else:
            value = func(*args, **kwargs) #type: ignore
            _ = r.set(key, pickle.dumps(value))
        return value #type: ignore
    return wrapper #type: ignore

global_cache = _redis_cache