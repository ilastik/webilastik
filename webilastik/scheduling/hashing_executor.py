# pyright: strict

from concurrent import futures
from concurrent.futures import Future
import queue
from typing import Any, Generic, Hashable, Optional, TypeVar, Callable, Set, List
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
        return False #FIXME

    def cancelled(self) -> bool:
        if self.future:
            return self.future.cancelled()
        return False

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
        _ = self.done_event.wait()
        if self.future is None:
            assert False, "expected future to be present!"
        return self.future.result(timeout)

    def exception(self, timeout: Optional[float] = None) -> Optional[BaseException]:
        if self.future:
            return self.future.exception()
        return None


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
                    # print(f"trying to get stuff from work queue")
                    priority_future = self._work_queue.get(timeout=2)
                except queue.Empty:
                    # print(f"Nothing on work queue. Retrying...")
                    continue
                print(f"got work from queue")
                if priority_future.group_id in self._cancelled_groups:
                    continue
                executor = self._get_executor(priority_future.arg)
                inner_future = executor.submit(priority_future.target, priority_future.arg)
                priority_future.set_future(inner_future)

        self.enqueuer_thread = threading.Thread(group=None, target=_enqueuer_target)
        self.enqueuer_thread.start()

    def _get_executor(self, arg: Hashable) -> ProcessPoolExecutor:
        return self._executors[hash(arg) % len(self._executors)]

    def __del__(self):
        self.shutdown()

    def shutdown(self, wait: bool = True):
        print("Shutting down!")
        self._finished = True
        for idx, executor in enumerate(self._executors):
            print(f"===> Shutting down executor {idx} from {self}")
            executor.shutdown(wait)
        self.enqueuer_thread.join()


    def submit(self, target: Callable[[IN], OUT], arg: IN) -> Future[OUT]:
        priority_future = PriorityFuture[IN, OUT](
            priority=WorkPriority.INTERACTIVE, group_id=uuid.uuid4(), target=target, arg=arg
        )
        self._work_queue.put(priority_future)
        return priority_future
