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

IN = TypeVar("IN", bound=Hashable)
OUT = TypeVar("OUT")



class WorkPriority(IntEnum):
    JOB = 100
    INTERACTIVE = 0


class PriorityFuture(Generic[IN, OUT], Future[OUT]):
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

    def __lt__(self, other: "PriorityFuture[Any, Any]") -> bool:
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
        target: Callable[[IN], None],
        args: Iterable[IN],
        on_progress: Optional[JobProgressCallback] = None,
        on_complete: Optional[JobCompletedCallback] = None,
    ):
        self.target = target
        self.args = args
        self.num_args: Optional[int] = None
        self.on_progress = on_progress
        self.on_complete = on_complete

        self.uuid = uuid.uuid4()
        self.status: Literal["pending", "running", "cancelled", "failed", "succeeded"] = "pending"

        self.num_completed_steps = 0
        self.lock = threading.Lock()

    def work_units(self) -> Iterator[PriorityFuture[IN, None]]:
        def done_callback(future: Future[None]): # FIXME
            with self.lock:
                self.num_completed_steps += 1
                num_completed_steps = self.num_completed_steps
                if self.status == "pending" or self.status == "running":
                    if future.cancelled():
                        self.status = "cancelled"
                    elif future.exception():
                        self.status = "failed"
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
            priority_future = PriorityFuture(
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




# Does not inherit from concurrent.futures.Executor because the typing there is looser (too many Any's)
class HashingExecutor:

    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or max(1, multiprocessing.cpu_count() - 1)
        self._executors = [ProcessPoolExecutor(max_workers=1) for _ in range(self.max_workers)]
        self._work_queue: "PriorityQueue[PriorityFuture[Any, Any]]" = PriorityQueue()
        self._cancelled_groups: Set[uuid.UUID] = set()
        self._finished = False

        def _enqueuer_target():
            while not self._finished:
                try:
                    priority_future = self._work_queue.get(timeout=2)
                except queue.Empty:
                    continue
                if priority_future.group_id in self._cancelled_groups:
                    continue
                executor = self._get_executor(priority_future.arg)
                inner_future = executor.submit(priority_future.target, priority_future.arg)
                priority_future.set_future(inner_future)
            print("Shutting down!")
            for idx, executor in enumerate(self._executors):
                print(f"===> Shutting down executor {idx} from {self}")
                executor.shutdown(wait=True)

            cancelled_futures = 0
            while True:
                try:
                    _ = self._work_queue.get_nowait().cancel()
                    cancelled_futures += 1
                except queue.Empty:
                    break
            print(f"Cancelled {cancelled_futures} futures")

        self.enqueuer_thread = threading.Thread(group=None, target=_enqueuer_target)
        self.enqueuer_thread.start()

    def _get_executor(self, arg: Hashable) -> ProcessPoolExecutor:
        return self._executors[hash(arg) % len(self._executors)]

    def __del__(self):
        self.shutdown()

    def shutdown(self, wait: bool = True):
        self._finished = True
        self.enqueuer_thread.join()


    def submit(self, target: Callable[[IN], OUT], arg: IN) -> Future[OUT]:
        priority_future = PriorityFuture[IN, OUT](
            priority=WorkPriority.INTERACTIVE, group_id=uuid.uuid4(), target=target, arg=arg
        )
        self._work_queue.put(priority_future)
        return priority_future

    def submit_job(
        self,
        *,
        target: Callable[[IN], None],
        args: Iterable[IN],
        on_progress: Optional[JobProgressCallback] = None,
        on_complete: Optional[JobCompletedCallback] = None
    ) -> Job[IN]:
        job = Job(
            target=target,
            args=args,
            on_progress=on_progress,
            on_complete=on_complete,
        )
        #FIXME: don't flood the queue with job steps. Maybe put the job itself in the queue?
        for unit_of_work in job.work_units():
            self._work_queue.put(unit_of_work)
        return job
