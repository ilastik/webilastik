#pyright: strict

import atexit
import threading
from concurrent.futures import Executor, ProcessPoolExecutor, ThreadPoolExecutor
from typing import Optional, Protocol
import multiprocessing as mp

from webilastik.scheduling import ExecutorGetter, ExecutorHint, SerialExecutor

class ExecutorFactory(Protocol):
    def __call__(self, *, max_workers: Optional[int]) -> Executor:
        ...

class ExecutorManager:
    def __init__(self, executor_factory: ExecutorFactory) -> None:
        self._lock = threading.Lock()
        self._executor: "Executor | None" = None
        self._executor_factory = executor_factory
        super().__init__()

    def get_executor(self, max_workers: Optional[int]) -> Executor:
        with self._lock:
            if self._executor is None:
                self._executor = self._executor_factory(max_workers=max_workers)
        return self._executor

    def shutdown(self):
        if self._executor:
            self._executor.shutdown(wait=False)

    def __del__(self):
        self.shutdown()


def _create_process_pool(max_workers: Optional[int]) -> ProcessPoolExecutor:
    return ProcessPoolExecutor(max_workers=8, mp_context=mp.get_context("spawn"))
_server_executor_manager = ExecutorManager(executor_factory=_create_process_pool)

_worker_thread_prefix = "worker_pool_thread_"
def _create_worker_thread_pool(max_workers: Optional[int]) -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=8, thread_name_prefix=_worker_thread_prefix)
_worker_thread_pool_manager = ExecutorManager(executor_factory=_create_worker_thread_pool)


def _get_executor(*, hint: ExecutorHint, max_workers: Optional[int] = None) -> Executor:
    if threading.current_thread().name.startswith(_worker_thread_prefix):
        print(f"!!!!!!!!!!!! {hint} needs an executor but already inside one !!!!!!!!!!!!!!!!")
        return SerialExecutor()
    if hint == "server_tile_handler":
        print(f"Is something requesting a pool already???????????????????")
        return _server_executor_manager.get_executor(max_workers=max_workers)
    if hint == "training":
        return SerialExecutor()
        # return _worker_thread_pool_manager.get_executor(max_workers=max_workers)
    elif hint == "sampling":
        return SerialExecutor()
    elif hint == "feature_extraction":
        return SerialExecutor()
        # return _worker_thread_pool_manager.get_executor(max_workers=max_workers)
    elif hint == "predicting":
        return SerialExecutor()
        # return _worker_thread_pool_manager.get_executor(max_workers=max_workers)
    elif hint == "any":
        return SerialExecutor()

def _shutdown_executors():
    print(f"Shutting down global executors....")
    _server_executor_manager.shutdown()
    _worker_thread_pool_manager.shutdown()

_ = atexit.register(_shutdown_executors)

get_executor: ExecutorGetter = _get_executor