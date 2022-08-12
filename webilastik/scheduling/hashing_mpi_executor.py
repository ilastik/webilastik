#pyright: strict
# pyright: reportMissingTypeStubs=true

import sys
import threading
import enum
from typing import Any, Dict, Sequence, TypeVar, Generic, Callable
from typing_extensions import ParamSpec
from concurrent.futures import Executor, Future
import functools

from mpi4py import MPI

_P = ParamSpec("_P")
_T = TypeVar("_T")

class _Stop:
    pass

@enum.unique
class Tags(enum.IntEnum):
    """Tags are arbitrary ints used to identify the type/purpose of a message in MPI"""

    TASK_DONE = 1  # workers send messages tagged with TASK_DONE when they finished processing a unit of work
    NEW_TASK = enum.auto()  # units of work are tagged with "NEW_TASK" and sent to workers for processing


class _Task(Generic[_T]):
    def __init__(self, target: Callable[[], _T], future_id: int) -> None:
        self.target = target
        self.future_id = future_id
        super().__init__()

    def __call__(self, worker: "Worker") -> "_TaskResult[_T]":
        try:
            result_value = self.target()
        except Exception as e:
            result_value = e
        return _TaskResult(worker=worker, future_id=self.future_id, value=result_value)


class _TaskResult(Generic[_T]):
    def __init__(self, worker: "Worker", future_id: int, value: "_T | Exception") -> None:
        self.future_id = future_id
        self.value = value
        super().__init__()


class Worker:
    def __init__(self) -> None:
        self.rank = MPI.COMM_WORLD.Get_rank()
        self.stopped = False
        super().__init__()

    def start(self):
        print(f"WORKER {self.rank}: Started", file=sys.stderr)
        while True:
            status = MPI.Status()
            task: "_Task[Any] | _Stop" = MPI.COMM_WORLD.recv(source=MPI.ANY_SOURCE, tag=Tags.NEW_TASK, status=status)
            print(f"WORKER {self.rank}: Got task", file=sys.stderr)
            if isinstance(task, _Stop):
                self.stopped = True
                break
            task_result = task(worker=self)
            MPI.COMM_WORLD.send(task_result, dest=status.Get_source(), tag=Tags.TASK_DONE)
        print(f"WORKER {self.rank}: Terminated", file=sys.stderr)


class _WorkerHandle:
    def __init__(self, rank: int) -> None:
        self.rank = rank
        self.stopped = False
        super().__init__()

    def submit(self, task: _Task[Any]):
        print(f"Sending task to remote worker {self.rank}...", file=sys.stderr)
        MPI.COMM_WORLD.send(task, dest=self.rank, tag=Tags.NEW_TASK)

    def stop(self):
        MPI.COMM_WORLD.send(_Stop(), dest=self.rank, tag=Tags.NEW_TASK)
        self.stopped = True #FIXME: maybe get confirmation that it actually stopped?



class HashingMpiExecutor(Executor):
    """Coordinates work amongst MPI processes.

    In order to use this class, applications must be launched with mpirun: e.g.: mpirun -N <num_workers> ilastik.py
    """

    def __init__(self):
        if MPI.COMM_WORLD.Get_rank() != 0:
            Worker().start()
            exit(0)
        self.rank = MPI.COMM_WORLD.Get_rank()
        self.num_workers = MPI.COMM_WORLD.size - 1
        if self.num_workers <= 0:
            raise ValueError("Trying to orchestrate tasks with {num_workers} workers")
        self._worker_handles: "Sequence[_WorkerHandle]" = [_WorkerHandle(rank=rank) for rank in range(1, self.num_workers + 1)]
        self._active_futures: Dict[int, Future[Any]] = {}
        self._lock = threading.Lock()
        self._shutting_down = False
        self._results_collector_thread = threading.Thread(group=None, target=self._collect_task_results)
        self._results_collector_thread.start()
        super().__init__()

    def _collect_task_results(self):
        stop_requested = False
        while not stop_requested or len(self._active_futures) > 0:
            task_result: "_TaskResult[Any] | _Stop" = MPI.COMM_WORLD.recv(source=MPI.ANY_SOURCE, tag=Tags.TASK_DONE)
            if isinstance(task_result, _Stop):
                stop_requested = True
                continue
            future = self._active_futures.pop(task_result.future_id)
            future.set_result(task_result.value)

    def _stop_result_collection(self):
        MPI.COMM_WORLD.send(_Stop(), dest=self.rank, tag=Tags.TASK_DONE)

    def submit(self, fn: Callable[_P, _T], *args: _P.args, **kwargs: _P.kwargs) -> Future[_T]:
        with self._lock:
            if self._shutting_down:
                raise RuntimeError("Executor is shutting down")
            future: Future[_T] = Future()
            task: _Task[_T] = _Task(functools.partial(fn, *args, **kwargs), future_id=id(future))
            self._active_futures[task.future_id] = future
            worker_index = hash((*args, *kwargs.items())) % len(self._worker_handles)#FIXME: it's possible the args are not hashable
            worker_handle = self._worker_handles[worker_index]
            worker_handle.submit(task)
            _ = future.set_running_or_notify_cancel()
            return future

    def shutdown(self, wait: bool = True):
        with self._lock:
            if self._shutting_down:
                return
            self._shutting_down = True
        for worker_handle in self._worker_handles:
            worker_handle.stop()
        MPI.COMM_WORLD.send(_Stop(), dest=self.rank, tag=Tags.TASK_DONE)
        self._results_collector_thread.join()
