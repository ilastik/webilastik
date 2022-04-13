#pyright: strict
#pyright: reportPrivateUsage=false

import queue
from typing import Callable, Generic, Iterable, Literal, Protocol, Any, TypeVar
from typing_extensions import ParamSpec
from collections.abc import Sized
from abc import ABC, abstractmethod
import threading
import uuid
import time
from concurrent.futures import Executor, Future
import functools
import enum

from ndstructs.utils.json_serializable import JsonObject

from webilastik.utility import PeekableIterator

IN = TypeVar("IN", covariant=True)
OUT = TypeVar("OUT")

class JobProgressCallback(Protocol):
    def __call__(self, job_id: uuid.UUID, step_index: int) -> Any:
        ...

class JobCompletedCallback(Protocol):
    def __call__(self, job_id: uuid.UUID) -> Any:
        ...

class Job(Generic[IN, OUT], Future[OUT]):
    def __init__(
        self,
        *,
        name: str,
        target: Callable[[IN], OUT],
        on_progress: "JobProgressCallback | None" = None,
        args: Iterable[IN],
        num_args: "int | None" = None,
    ):
        super().__init__()
        self.creation_time = time.time()
        self.name = name
        self.target = target
        self.on_progress: "JobProgressCallback | None" = on_progress
        self.num_args: "int | None" = num_args or (len(args) if isinstance(args, Sized) else None)
        self.args: PeekableIterator[IN] = PeekableIterator(args)

        self.uuid: uuid.UUID = uuid.uuid4()
        self.num_completed_steps = 0
        self.num_dispatched_steps = 0
        self.job_lock = threading.Lock()

    def _get_next_task(self) -> "_JobStepTask[OUT] | None":
        with self.job_lock:
            if self.done() or not self.args.has_next():
                return None
            if not self.running():
                _ = self.set_running_or_notify_cancel()
            step_index = self.num_dispatched_steps
            self.num_dispatched_steps += 1
            if not self.args.has_next():
                self.num_args = self.num_dispatched_steps #FIXME

        def step_done_callback(future: Future[Any]): # FIXME
            with self.job_lock:
                self.num_completed_steps += 1
                if self.done():
                    pass
                elif future.cancelled():
                    _ = self.cancel()
                elif future.exception():
                    self.set_exception(future.exception())
                elif not self.args.has_next() and self.num_dispatched_steps == self.num_completed_steps:
                    result = future.result()
                    self.set_result(result)
            if self.on_progress:
                self.on_progress(self.uuid, step_index)

        return _JobStepTask(
            job=self,
            fn=functools.partial(self.target, self.args.get_next()),
            inner_future_done_callback=step_done_callback,
        )

    def to_json_value(self) -> JsonObject:
        error_message: "str | None" = None
        with self.job_lock:
            if self.cancelled():
                status = "cancelled"
            elif self.done():
                exception = self.exception() # only call exception() if done() so we don't block
                if exception:
                    status = "failed"
                    error_message = str()
                else:
                    status = "success"
            elif self.running():
                status = "running"
            else:
                status = "pending"

            return {
                "name": self.name,
                "num_args": self.num_args,
                "uuid": str(self.uuid),
                "status": status,
                "num_completed_steps": self.num_completed_steps,
                "error_message": error_message
            }


_P = ParamSpec("_P")
_T = TypeVar("_T")

class _TaskPriority(enum.IntEnum):
    SHUT_DOWN = 0
    NORMAL = 10
    JOB = 100

class _Task(ABC,  Generic[_T]):
    def __init__(
        self,
        *,
        priority: _TaskPriority,
    ) -> None:
        self.priority = priority
        self.creation_time = time.time()
        self.uuid = uuid.uuid4()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, _Task):
            raise TypeError("Can't compare {self} to {other}")
        return (self.priority, self.creation_time) < (other.priority, other.creation_time)

    @abstractmethod
    def launch(self, executor: "PriorityExecutor") -> "None | Future[Any]":
        pass

    @abstractmethod
    def cancel(self) -> bool:
        pass

class _ShutDownTask(_Task[None]):
    def __init__(self, wait: bool) -> None:
        super().__init__(priority=_TaskPriority.SHUT_DOWN)
        self.wait = wait

    def cancel(self) -> bool:
        return True

    def launch(self, executor: "PriorityExecutor") -> None:
        with executor._lock:
            executor._status = "shutting_down"

        while True:
            try:
                leftover_task = executor._task_queue.get_nowait()
                if not self.wait:
                    _ = leftover_task.cancel()
                    continue
                if isinstance(leftover_task, _ShutDownTask):
                    continue
                if isinstance(leftover_task, _JobStepTask):
                    next_job_task = leftover_task
                    while next_job_task:
                        _ = next_job_task.launch(executor)
                        next_job_task = next_job_task.job._get_next_task()
                else:
                    _ = leftover_task.launch(executor)
            except queue.Empty:
                break
        executor._wrapped_executor.shutdown(wait=self.wait)
        executor._status = "done"
        return None

class _JobStepTask(_Task[_T]):
    def __init__(self, *, job: Job[Any, _T], fn: Callable[[], _T], inner_future_done_callback: "Callable[[Future[_T]], None]") -> None:
        super().__init__(priority=_TaskPriority.JOB)
        self.fn = fn
        self.job = job
        self.inner_future_done_callback = inner_future_done_callback

    def launch(self, executor: "PriorityExecutor") -> "None | Future[Any]":
        inner_future = executor._wrapped_executor.submit(self.fn)
        inner_future.add_done_callback(self.inner_future_done_callback)

        def enqueue_next_job_step(future: Future[Any]):
            with executor._lock:
                if executor._status != "ready":
                    return
                next_task = self.job._get_next_task()
                if not next_task:
                    return
                executor._task_queue.put(next_task)
        inner_future.add_done_callback(enqueue_next_job_step)
        return inner_future

    def cancel(self) -> bool:
        return self.job.cancel()

class _StandaloneTask(_Task[_T]):
    def __init__(
        self,
        *,
        fn: Callable[[], _T],
    ) -> None:
        self.fn = fn
        self.outer_future: "Future[_T]" = Future()
        super().__init__(priority=_TaskPriority.NORMAL)

    def cancel(self) -> bool:
        return self.outer_future.cancel()

    def launch(self, executor: "PriorityExecutor") -> "None | Future[Any]":
        if not self.outer_future.set_running_or_notify_cancel():
            return None

        inner_future = executor._wrapped_executor.submit(self.fn)

        def finish_outer_future(inner_future: Future[Any]):
            try:
                if inner_future.cancelled():
                    _ = self.outer_future.cancel()
                elif inner_future.exception():
                    _ = self.outer_future.set_exception(inner_future.exception())
                else:
                    self.outer_future.set_result(inner_future.result())
            except Exception as e:
                print(f"Error when reporting future result: {e}") #FIXME?
        inner_future.add_done_callback(finish_outer_future)
        return inner_future


class PriorityExecutor(Executor):
    def __init__(self, executor: Executor, num_concurrent_tasks: int) -> None:
        self._lock = threading.Lock()
        self._task_semaphore = threading.Semaphore(value=num_concurrent_tasks)
        self._status: Literal["ready", "shutting_down", "done"] = "ready"
        self._wrapped_executor: Executor = executor
        self._task_queue: "queue.PriorityQueue[_StandaloneTask[Any] | _JobStepTask[Any] | _ShutDownTask]" = queue.PriorityQueue()

        self._enqueueing_thread = threading.Thread(group=None, target=self._enqueueing_target)
        self._enqueueing_thread.start()

    def shutdown(self, wait: bool = True) -> None:
        with self._lock:
            if self._status != "ready":
                return
            self._status = "shutting_down"
        self._task_queue.put(_ShutDownTask(wait=wait))
        self._enqueueing_thread.join()

    def __del__(self):
        self.shutdown(wait=True)

    def submit(self, fn: Callable[_P, _T], *args: _P.args, **kwargs: _P.kwargs) -> Future[_T]:
        with self._lock:
            if self._status != "ready":
                raise Exception("Executor is shutting down")
            task = _StandaloneTask(fn=functools.partial(fn, *args, **kwargs))
            self._task_queue.put(task)
            return task.outer_future

    def submit_job(self, job: Job[Any, Any]):
        with self._lock:
            if self._status != "ready":
                raise Exception("Executor is shutting down")
            job_step_task = job._get_next_task()
            if job_step_task:
                self._task_queue.put(job_step_task)

    def _enqueueing_target(self):
        while True:
            _ = self._task_semaphore.acquire()
            task = self._task_queue.get()
            future = task.launch(self)
            if future:
                future.add_done_callback(lambda _: self._task_semaphore.release())
            else:
                self._task_semaphore.release()
            if isinstance(task, _ShutDownTask):
                return
