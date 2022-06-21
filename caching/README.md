# Caching implementations

You can change ilastik's caching implementation by implementing a `global_cache` module that exports the `global_cache` function decorator.

Select one in load-time by setting `PYTHONPATH`, e.g.:

`PYTHONPATH=./caching/redis_cache python webilastik/server/session_allocator.py`