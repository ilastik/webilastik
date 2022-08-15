#pyright: strict

from abc import ABC, abstractmethod
import atexit
import threading
from concurrent.futures import Executor, ThreadPoolExecutor, ProcessPoolExecutor
from typing import Optional
import multiprocessing as mp
import sys

from webilastik.scheduling import ExecutorGetter, ExecutorHint, SerialExecutor
from webilastik.scheduling.hashing_mpi_executor import HashingMpiExecutor
from webilastik.scheduling.mpi_comm_executor_wrapper import MPICommExecutorWrapper


class ExecutorManager(ABC):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._executor: "Executor | None" = None
        super().__init__()

    @abstractmethod
    def _create_executor(self, max_workers: Optional[int]) -> Executor:
        raise NotImplementedError()

    def get_executor(self, max_workers: Optional[int]) -> Executor:
        with self._lock:
            if self._executor is None:
                self._executor = self._create_executor(max_workers=max_workers)
        return self._executor

    def shutdown(self):
        if self._executor:
            self._executor.shutdown(wait=False)

    def __del__(self):
        self.shutdown()

class MPICommExecutorManager(ExecutorManager):
    def _create_executor(self, max_workers: Optional[int]) -> Executor:
        return MPICommExecutorWrapper()

class HashingMpiExecutorManager(ExecutorManager):
    def _create_executor(self, max_workers: Optional[int]) -> Executor:
        return HashingMpiExecutor()

class ProcessPoolExecutorManager(ExecutorManager):
    def _create_executor(self, max_workers: Optional[int]) -> Executor:
        return ProcessPoolExecutor(max_workers=10, mp_context=mp.get_context("spawn"))

class ThreadPoolExecutorManager(ExecutorManager):
    WORKER_THERAD_PREFIX = "worker_pool_thread_"

    def _create_executor(self, max_workers: Optional[int]) -> Executor:
        return ThreadPoolExecutor(max_workers=10, thread_name_prefix=self.WORKER_THERAD_PREFIX)


_server_executor_manager = ProcessPoolExecutorManager()
_worker_thread_pool_manager = ThreadPoolExecutorManager()


def _get_executor(*, hint: ExecutorHint, max_workers: Optional[int] = None) -> Executor:
    if threading.current_thread().name.startswith(ThreadPoolExecutorManager.WORKER_THERAD_PREFIX):
        print(f"[WARNING]{hint} needs an executor but already inside one", file=sys.stderr)
        return SerialExecutor()
    if hint == "server_tile_handler":
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
        # return SerialExecutor()
        return _worker_thread_pool_manager.get_executor(max_workers=max_workers)
    elif hint == "any":
        return SerialExecutor()

def _shutdown_executors():
    print(f"Shutting down global executors....")
    _server_executor_manager.shutdown()
    _worker_thread_pool_manager.shutdown()

_ = atexit.register(_shutdown_executors)

get_executor: ExecutorGetter = _get_executor