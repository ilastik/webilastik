#pyright: strict

from concurrent.futures import Executor, ThreadPoolExecutor
from typing import Optional
from webilastik.scheduling import ExecutorGetter, ExecutorHint, SerialExecutor

_training_pool = ThreadPoolExecutor()

def _get_executor(*, hint: ExecutorHint, max_workers: Optional[int] = None) -> Executor:
    if hint == "training":
        return _training_pool
    elif hint == "sampling":
        return SerialExecutor()
    elif hint == "predicting":
        return SerialExecutor()
    elif hint == "any":
        return SerialExecutor()

get_executor: ExecutorGetter = _get_executor