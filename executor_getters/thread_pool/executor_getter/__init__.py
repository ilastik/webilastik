from concurrent.futures import Executor, ThreadPoolExecutor
from typing import Optional
from webilastik.scheduling import ExecutorGetter, ExecutorHint

def _get_thread_pool_executor(*, hint: ExecutorHint, max_workers: Optional[int] = None) -> Executor:
    return ThreadPoolExecutor(max_workers=max_workers)

get_executor: ExecutorGetter = _get_thread_pool_executor