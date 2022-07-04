from concurrent.futures import Executor, ProcessPoolExecutor
from typing import Optional
from webilastik.scheduling import ExecutorGetter, ExecutorHint

def _get_process_pool_executor(*, hint: ExecutorHint, max_workers: Optional[int] = None) -> Executor:
    return ProcessPoolExecutor(max_workers=max_workers)

get_executor: ExecutorGetter = _get_process_pool_executor