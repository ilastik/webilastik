#pyright: strict

from abc import ABC, abstractmethod
import atexit
import threading
from concurrent.futures import Executor, ThreadPoolExecutor
from typing import Optional, List
import sys

from webilastik.scheduling import ExecutorGetter, ExecutorHint, SerialExecutor


_executor_managers: List["ExecutorManager"] = []

def _shutdown_executors():
    print(f"Shutting down global executors....")
    for manager in _executor_managers:
        manager.shutdown()

_ = atexit.register(_shutdown_executors)

class ExecutorManager(ABC):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._executor: "Executor | None" = None
        super().__init__()
        _executor_managers.append(self)

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

from webilastik.scheduling.mpi_comm_executor_wrapper import MPICommExecutorWrapper
class MpiCommExecutorManager(ExecutorManager):
    def _create_executor(self, max_workers: Optional[int]) -> MPICommExecutorWrapper:
        return MPICommExecutorWrapper()

class ThreadPoolExecutorManager(ExecutorManager):
    WORKER_THREAD_PREFIX = "worker_pool_thread_"

    def _create_executor(self, max_workers: Optional[int]) -> Executor:
        import os
        cpus_per_task = int(os.environ["SLURM_CPUS_PER_TASK"])
        # FIXME: do we really have to sacrifice this many threads just for executor secret threads?
        return ThreadPoolExecutor(max_workers=cpus_per_task - 2, thread_name_prefix=self.WORKER_THREAD_PREFIX)


_server_executor_manager = MpiCommExecutorManager()
_worker_thread_pool_manager = ThreadPoolExecutorManager()


def _get_executor(*, hint: ExecutorHint, max_workers: Optional[int] = None) -> Executor:
    if threading.current_thread().name.startswith(ThreadPoolExecutorManager.WORKER_THREAD_PREFIX):
        print(f"[WARNING]{hint} needs an executor but already inside one", file=sys.stderr)
        return SerialExecutor()
    if hint == "server_tile_handler":
        return _server_executor_manager.get_executor(max_workers=max_workers)
    if hint == "training":
        return SerialExecutor()
    elif hint == "sampling":
        return SerialExecutor()
    elif hint == "feature_extraction":
        return _worker_thread_pool_manager.get_executor(max_workers=max_workers)
    elif hint == "predicting":
        return _worker_thread_pool_manager.get_executor(max_workers=max_workers)
    elif hint == "any":
        return SerialExecutor()

get_executor: ExecutorGetter = _get_executor