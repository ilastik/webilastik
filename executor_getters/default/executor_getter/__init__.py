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
    return ProcessPoolExecutor(max_workers=max_workers, mp_context=mp.get_context("spawn"))

_server_executor_manager = ExecutorManager(executor_factory=_create_process_pool)
_training_executor_manager = ExecutorManager(executor_factory=ThreadPoolExecutor)
# _sampling_executor_manager = ExecutorManager(executor_factory=ThreadPoolExecutor)


def _get_executor(*, hint: ExecutorHint, max_workers: Optional[int] = None) -> Executor:
    if hint == "server_tile_handler":
        return _server_executor_manager.get_executor(max_workers=max_workers)
    if hint == "training":
        return _training_executor_manager.get_executor(max_workers=max_workers)
    elif hint == "sampling":
        return _training_executor_manager.get_executor(max_workers=max_workers)
    elif hint == "predicting":
        return SerialExecutor()
    elif hint == "any":
        return SerialExecutor()

def _shutdown_executors():
    print(f"Shutting down global executors....")
    _training_executor_manager.shutdown()

_ = atexit.register(_shutdown_executors)

get_executor: ExecutorGetter = _get_executor