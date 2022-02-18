#pyright: strict
# pyright: reportMissingTypeStubs=true

import threading
import queue
import enum
from typing import Any, Dict, TypeVar, Generic, Callable
import uuid
import logging
from concurrent.futures import Future

from mpi4py import MPI

logger = logging.getLogger(__name__)

T = TypeVar("T")

class _Stop:
    pass

@enum.unique
class Tags(enum.IntEnum):
    """Tags are arbitrary ints used to identify the type/purpose of a message in MPI"""

    TASK_DONE = 1  # workers send messages tagged with TASK_DONE when they finished processing a unit of work
    NEW_TASK = enum.auto()  # units of work are tagged with "NEW_TASK" and sent to workers for processing


class _Task(Generic[T]):
    def __init__(self, target: Callable[[], T], task_id: uuid.UUID, group_id: uuid.UUID, priority: int) -> None:
        self.target = target
        self.task_id = task_id
        self.group_id = group_id
        self.priority = priority

    def __lt__(self, other: "_Task[T] | _Stop") -> bool:
        if isinstance(other, _Stop):
            return False
        return self.priority < other.priority

    def __call__(self, worker: "_Worker") -> "_TaskResult[T]":
        try:
            result_value = self.target()
        except Exception as e:
            result_value = e
        return _TaskResult(worker=worker, task_id=self.task_id, value=result_value)


class _TaskResult(Generic[T]):
    def __init__(self, worker: "_Worker", task_id: uuid.UUID, value: "T | Exception") -> None:
        self.worker = worker
        self.task_id: uuid.UUID
        self.value = value


class _Worker:
    def __init__(self, rank: int) -> None:
        self.rank = rank
        self.stopped = False

    def start(self):
        logger.info(f"WORKER {self.rank}: Started")
        while True:
            status = MPI.Status()
            task: "_Task[Any] | _Stop" = MPI.COMM_WORLD.recv(source=MPI.ANY_SOURCE, tag=Tags.NEW_TASK, status=status)
            if isinstance(task, _Stop):
                break
            task_result = task(worker=self)
            MPI.COMM_WORLD.send(task_result, dest=status.Get_source(), tag=Tags.TASK_DONE)
        logger.info(f"WORKER {self.rank}: Terminated")

    def submit(self, task: _Task[Any]):
        logger.debug(f"Sending task to remote worker {self.rank}...")
        MPI.COMM_WORLD.send(task, dest=self.rank, tag=Tags.NEW_TASK)

    def stop(self):
        MPI.COMM_WORLD.send(_Stop(), dest=self.rank, tag=Tags.NEW_TASK)
        self.stopped = True


class MpiExecutor:
    """Coordinates work amongst MPI processes.

    In order to use this class, applications must be launched with mpirun: e.g.: mpirun -N <num_workers> ilastik.py
    """

    def __init__(self):
        self.rank = MPI.COMM_WORLD.Get_rank()
        self.num_workers = MPI.COMM_WORLD.size - 1
        if self.num_workers <= 0:
            raise ValueError("Trying to orchestrate tasks with {num_workers} workers")

        self._idle_workers: "queue.Queue[_Worker]" = queue.Queue()
        for rank in range(1, self.num_workers + 1):
            self._idle_workers.put(_Worker(rank=rank))

        self._tasks: "queue.PriorityQueue[ _Task[Any] | _Stop ]" = queue.PriorityQueue()
        self._tracked_futures: Dict[uuid.UUID, Future[Any]] = {}

        self._lock = threading.Lock()
        self._shutting_down = False
        self._enqueueing_thread = threading.Thread(group=None, target=self._issue_work)
        self._enqueueing_thread.start()
        self._collecting_thread = threading.Thread(group=None, target=self._collect_results)
        self._collecting_thread.start()

    def _wait_for_task_result(self) -> "_TaskResult[Any] | _Stop":
        return MPI.COMM_WORLD.recv(source=MPI.ANY_SOURCE, tag=Tags.TASK_DONE)

    def _stop_result_collection(self):
        MPI.COMM_WORLD.send(_Stop(), dest=self.rank, tag=Tags.TASK_DONE)

    def _drain_tasks(self):
        while True:
            try:
                _ = self._tasks.get_nowait()
            except queue.Empty:
                return

    def _issue_work(self):
        while True:
            task = self._tasks.get()

            if isinstance(task, _Stop):
                self._drain_tasks()
                self._stop_result_collection()
                return

            with self._lock:
                canceled = not self._tracked_futures[task.task_id].set_running_or_notify_cancel()
                if canceled:
                    del self._tracked_futures[task.task_id]
                    continue

            self._idle_workers.get().submit(task)

    def _stop_workers_and_drop_futures(self):
        while True:
            try:
                worker = self._idle_workers.get_nowait()
                worker.stop()
            except queue.Empty:
                break
        while self._tracked_futures:
            _, future = self._tracked_futures.popitem()
            _ = future.cancel()
            task_result = self._wait_for_task_result()
            assert isinstance(task_result, _TaskResult)
            task_result.worker.stop()

    def _collect_results(self):
        while True:
            command = self._wait_for_task_result()

            if isinstance(command, _Stop):
                self._stop_workers_and_drop_futures()
                return

            with self._lock:
                if isinstance(command.value, Exception):
                    self._tracked_futures[command.task_id].set_exception(command.value)
                else:
                    self._tracked_futures[command.task_id].set_result(command.value)
            self._idle_workers.put(command.worker)

    def submit(self, target: Callable[[], T], priority: int, task_id: "uuid.UUID | None", group_id: "uuid.UUID | None") -> Future[T]:
        with self._lock:
            if self._shutting_down:
                raise Exception("Executor is shutting down")
            task = _Task(target=target, task_id=task_id or uuid.uuid4(), group_id=group_id or uuid.uuid4(), priority=priority)
            future = Future[T]()
            self._tracked_futures[task.task_id] = future
        self._tasks.put(task)
        return future

    def shutdown(self):
        with self._lock:
            if self._shutting_down:
                return
            self._shutting_down = True
            self._tasks.put(_Stop())

if MPI.COMM_WORLD.Get_rank() != 0:
    # FIXME? is there a more elegant way to handle this?
    _Worker(rank=MPI.COMM_WORLD.Get_rank()).start()
