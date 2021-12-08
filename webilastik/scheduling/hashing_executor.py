# pyright: strict

from concurrent import futures
from concurrent.futures import Future, TimeoutError
import queue
from typing import Any, Generic, Hashable, Iterable, Iterator, Literal, Optional, Protocol, TypeVar, Callable, Set, List
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import time
from enum import IntEnum
from queue import PriorityQueue
import uuid
import threading

from ndstructs.utils.json_serializable import JsonObject

IN = TypeVar("IN", bound=Hashable)
OUT = TypeVar("OUT")



class WorkPriority(IntEnum):
    JOB = 100
    INTERACTIVE = 10
    CONTROL = 1


class _PriorityFuture(Generic[IN, OUT], Future[OUT]):
    def __init__(
        self,
        *,
        priority: WorkPriority,
        group_id: uuid.UUID,
        target: Callable[[IN], OUT],
        arg: IN,
    ) -> None:
        self.priority = priority
        self.group_id = group_id
        self.creation_time = time.time()

        self.target = target
        self.arg = arg

        self.future: Optional[Future[OUT]] = None
        self.lock = threading.Lock()
        self.done_callbacks: List[Callable[[Future[OUT]], Any]] = []
        self.done_event = threading.Event()
        self._cancelled = False

    def __lt__(self, other: "_PriorityFuture[Any, Any]") -> bool:
        return (self.priority, self.creation_time) < (other.priority, other.creation_time)

    def set_future(self, future: Future[OUT]):
        with self.lock:
            self.future = future
            if self._cancelled:
                _ = self.future.cancel()
            future.add_done_callback(lambda _: self.done_event.set())
            while self.done_callbacks:
                future.add_done_callback(self.done_callbacks.pop(0))

    def cancel(self) -> bool:
        with self.lock:
            self._cancelled = True
            if self.future:
                return self.future.cancel()
            self.done_event.set()
        return False #FIXME

    def cancelled(self) -> bool:
        if self.future:
            return self.future.cancelled()
        return self._cancelled

    def running(self) -> bool:
        if self.future:
            return self.future.running()
        return False

    def done(self) -> bool:
        if self.future:
            return self.future.done()
        return False

    def add_done_callback(self, fn: Callable[[futures.Future[OUT]], Any]) -> None:
        with self.lock:
            if self.future:
                self.future.add_done_callback(fn)
            else:
                self.done_callbacks.append(fn)

    def result(self, timeout: Optional[float] = None) -> OUT:
        t0 = time.time()
        if not self.done_event.wait(timeout):
            raise TimeoutError
        assert self.future != None, "expected future to be present!"
        time_spent_waiting = time.time() - t0
        leftover_timeout = None if timeout is None else max(0, timeout - time_spent_waiting)
        return self.future.result(leftover_timeout)

    def exception(self, timeout: Optional[float] = None) -> Optional[BaseException]:
        if self.future:
            return self.future.exception()
        return None


class EndWorker(_PriorityFuture[Any, Any]):
    def __init__(self) -> None:
        super().__init__(
            priority=WorkPriority.CONTROL,
            group_id=uuid.uuid4(),
            target=lambda _: None,
            arg=None
        )

class JobProgressCallback(Protocol):
    def __call__(self, job_id: uuid.UUID, step_index: int) -> Any:
        ...

class JobCompletedCallback(Protocol):
    def __call__(self, job_id: uuid.UUID) -> Any:
        ...

class Job(Generic[IN]):
    def __init__(
        self,
        *,
        name: str,
        target: Callable[[IN], None],
        args: Iterable[IN],
        on_progress: Optional[JobProgressCallback] = None,
        on_complete: Optional[JobCompletedCallback] = None,
    ):
        self.name = name
        self.target = target
        self.args = args
        self.num_args: Optional[int] = None
        self.on_progress = on_progress
        self.on_complete = on_complete

        self.uuid = uuid.uuid4()
        self.status: Literal["pending", "running", "cancelled", "failed", "succeeded"] = "pending"

        self.num_completed_steps = 0
        self.lock = threading.Lock()

    def work_units(self) -> Iterator[_PriorityFuture[IN, None]]:
        def done_callback(future: Future[None]): # FIXME
            with self.lock:
                self.num_completed_steps += 1
                num_completed_steps = self.num_completed_steps
                if self.status == "pending" or self.status == "running":
                    if future.cancelled():
                        self.status = "cancelled"
                    elif future.exception():
                        self.status = "failed"
                        print(future.exception())
                    elif self.num_args == None:
                        self.status = "running"
                    else:
                        if num_completed_steps < self.num_args:
                            self.status = "running"
                        else:
                            self.status = "succeeded"
                            if self.on_complete:
                                self.on_complete(self.uuid)
            if self.on_progress:
                self.on_progress(self.uuid, num_completed_steps)

        num_args = 0
        for arg in self.args:
            num_args += 1
            priority_future = _PriorityFuture(
                priority=WorkPriority.JOB, group_id=self.uuid, target=self.target, arg=arg
            )
            priority_future.add_done_callback(done_callback)
            yield priority_future

        with self.lock:
            self.num_args = num_args
            if self.num_completed_steps == num_args and self.status == "pending" or self.status == "running":
                self.status = "succeeded"
                if self.on_complete:
                    self.on_complete(self.uuid)

    def to_json_value(self) -> JsonObject:
        with self.lock:
            return {
                "name": self.name,
                "num_args": self.num_args,
                "uuid": str(self.uuid),
                "status": self.status,
                "num_completed_steps": self.num_completed_steps,
            }


class _Worker:
    def __init__(self, *, name: str) -> None:
        self.name = name
        self._executor = ProcessPoolExecutor(max_workers=1)
        self._work_queue: "PriorityQueue[_PriorityFuture[Any, Any]]" = PriorityQueue()
        self._cancelled_groups: Set[uuid.UUID] = set()
        self._shutting_down = False
        self._lock = threading.Lock()
        self._executor_is_free = threading.Event()
        self._executor_is_free.set()

        self.enqueuer_thread = threading.Thread(group=None, target=self._enqueuer_target)
        self.enqueuer_thread.start()

    def submit_work(self, priority_future: _PriorityFuture[Any, Any]):
        with self._lock:
            if self._shutting_down:
                raise Exception(f"_Worker {self.name} has shut down")
            self._work_queue.put(priority_future)

    def _enqueuer_target(self):
        while True:
            _ = self._executor_is_free.wait()
            self._executor_is_free.clear()

            priority_future = self._work_queue.get()
            if isinstance(priority_future, EndWorker):
                self._executor.shutdown(wait=True)
                while True:
                    try:
                        _ = self._work_queue.get_nowait().cancel()
                    except queue.Empty:
                        return
            if priority_future.group_id in self._cancelled_groups:
                _ = priority_future.cancel()
                continue
            inner_future = self._executor.submit(priority_future.target, priority_future.arg)
            inner_future.add_done_callback(lambda _: self._executor_is_free.set())
            priority_future.set_future(inner_future)

    def cancel_group(self, group_id: uuid.UUID):
        with self._lock:
            self._cancelled_groups.add(group_id)

    def shutdown(self, wait: bool = True):
        with self._lock:
            if self._shutting_down:
                return
            self._shutting_down = True
            self._work_queue.put(EndWorker())
            self._executor_is_free.set()
            self.enqueuer_thread.join()

    def __del__(self):
        self.shutdown()

# Does not inherit from concurrent.futures.Executor because the typing there is looser (too many Any's)
class HashingExecutor:
    def __init__(self, name: str, max_workers: Optional[int] = None):
        self.max_workers = max_workers or max(1, multiprocessing.cpu_count() - 1)
        self._workers = [
            _Worker(name=f"{name} worker {i}") for i in range(self.max_workers)
        ]

    def shutdown(self, wait: bool = True):
        for executor in self._workers:
            executor.shutdown(wait)

    def __del__(self):
        self.shutdown()

    def _get_worker(self, arg: Hashable) -> _Worker:
        return self._workers[hash(arg) % len(self._workers)]

    def submit(self, target: Callable[[IN], OUT], arg: IN) -> Future[OUT]:
        priority_future = _PriorityFuture[IN, OUT](
            priority=WorkPriority.INTERACTIVE, group_id=uuid.uuid4(), target=target, arg=arg
        )
        self._get_worker(arg).submit_work(priority_future)
        return priority_future

    def submit_job(
        self,
        *,
        name: str,
        target: Callable[[IN], None],
        args: Iterable[IN],
        on_progress: Optional[JobProgressCallback] = None,
        on_complete: Optional[JobCompletedCallback] = None
    ) -> Job[IN]:
        job = Job(
            name=name,
            target=target,
            args=args,
            on_progress=on_progress,
            on_complete=on_complete,
        )
        #FIXME: don't flood the queue with job steps. Maybe put the job itself in the queue?
        for priority_future in job.work_units():
            executor = self._get_worker(priority_future.arg)
            executor.submit_work(priority_future)
        return job

    def cancel_group(self, group_id: uuid.UUID):
        for worker in self._workers:
            worker.cancel_group(group_id)
