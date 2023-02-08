#pyright: strict

from abc import ABC, abstractmethod
import atexit
import threading
from concurrent.futures import Executor, ThreadPoolExecutor
from typing import Optional
import sys

from webilastik.scheduling import ExecutorGetter, ExecutorHint, SerialExecutor

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

class DaskExecutorManager(ExecutorManager):
    def _create_executor(self, max_workers: Optional[int]) -> Executor:
        from dask_mpi import initialize # type: ignore
        _ = initialize()

        from dask.distributed import Client
        client = Client()  # Connect this local process to remote workers
        return client.get_executor() # pyright: ignore [reportUnknownMemberType]

class ThreadPoolExecutorManager(ExecutorManager):
    WORKER_THREAD_PREFIX = "worker_pool_thread_"

    def _create_executor(self, max_workers: Optional[int]) -> Executor:
        import multiprocessing
        import os
        slurm_cpus_per_task = os.environ.get("SLURM_CPUS_PER_TASK") 
        if slurm_cpus_per_task is not None:
            max_workers = int(slurm_cpus_per_task) - 3
        else:
            max_workers = multiprocessing.cpu_count()
        return ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=self.WORKER_THREAD_PREFIX)


# _server_executor_manager = MPICommExecutorManager()
# _server_executor_manager = HashingMpiExecutorManager()
_server_executor_manager = DaskExecutorManager()
_worker_thread_pool_manager = ThreadPoolExecutorManager()


def _get_executor(*, hint: ExecutorHint, max_workers: Optional[int] = None) -> Executor:
    if threading.current_thread().name.startswith(ThreadPoolExecutorManager.WORKER_THREAD_PREFIX):
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
        # return SerialExecutor()
        return _worker_thread_pool_manager.get_executor(max_workers=max_workers)
    elif hint == "predicting":
        # return SerialExecutor()
        return _worker_thread_pool_manager.get_executor(max_workers=max_workers)
    elif hint == "any":
        return SerialExecutor()

def _shutdown_executors():
    print(f"Shutting down server executor.......")
    _server_executor_manager.shutdown()
    print(f"Shutting down thread pool.......")
    _worker_thread_pool_manager.shutdown()
    print("Done shutting down executors.........................")

_ = atexit.register(_shutdown_executors)

get_executor: ExecutorGetter = _get_executor