#pyright: strict
#pyright: reportPrivateUsage=false

from abc import ABC, abstractmethod
import queue
from typing import Callable, Generic, Iterable, Literal, Protocol, Any, TypeVar, List, Union
from typing_extensions import ParamSpec, TypeAlias
from collections.abc import Sized
import threading
import uuid
import time
from concurrent.futures import Executor, Future
import functools
from dataclasses import dataclass
from datetime import datetime, timezone
from webilastik.server.rpc.dto import JobCanceledDto, JobDto, JobFinishedDto, JobIsPendingDto, JobIsRunningDto

from webilastik.utility import Empty, PeekableIterator

_IN = TypeVar("_IN", covariant=True)
_OK = TypeVar("_OK")
_ERR = TypeVar("_ERR", bound=Exception)
_P = ParamSpec("_P")


@dataclass
class JobFinished(Generic[_OK, _ERR]):
    result: "_OK | _ERR"

    def to_dto(self) -> JobFinishedDto:
        # FIXME: is it fair to check here if result is an Exception? should this be generic over _ERR?
        return JobFinishedDto(
            error_message=str(self.result) if isinstance(self.result, Exception) else None
        )

@dataclass
class JobIsPending:
    def to_dto(self) -> JobIsPendingDto:
        return JobIsPendingDto()

@dataclass
class JobIsRunning:
    num_completed_steps: int
    num_dispatched_steps: int

    def to_dto(self) -> JobIsRunningDto:
        return JobIsRunningDto(num_completed_steps=self.num_completed_steps, num_dispatched_steps=self.num_dispatched_steps)

@dataclass
class JobCanceled:
    message: str

    def to_dto(self) -> JobCanceledDto:
        return JobCanceledDto(message=self.message)

JobStatus: TypeAlias = Union[JobFinished[_OK, _ERR], JobIsPending, JobIsRunning, JobCanceled]

class JobProgressCallback(Protocol):
    def __call__(self, *, job_id: uuid.UUID, step_index: int) -> Any:
        ...

JOB_OUT = TypeVar("JOB_OUT", contravariant=True)
class JobFinishedCallback(Protocol[JOB_OUT]):
    def __call__(self, *, job_id: uuid.UUID, output: JOB_OUT) -> Any:
        ...

class Job(Generic[_OK, _ERR], ABC):
    def __init__(self, name: str, num_args: "int | None") -> None:
        super().__init__()
        self.name = name
        self.num_args = num_args
        self.creation_time = datetime.now(timezone.utc)
        self.job_lock = threading.Lock()
        self.uuid: uuid.UUID = uuid.uuid4()
        self._status: JobStatus[_OK, _ERR] = JobIsPending()
        self.on_complete_callbacks: List[Callable[["JobCanceled | JobFinished[_OK, _ERR]"], None]] = []

    def to_dto(self) -> JobDto:
        return JobDto(
            name=self.name,
            num_args=self.num_args,
            uuid=str(self.uuid),
            status=self._status.to_dto(),
        )

    def __lt__(self, other: object) -> bool:
        if isinstance(other, (_Shutdown, _Task)):
            return False
        assert isinstance(other, Job)
        return self.creation_time < other.creation_time

    @abstractmethod
    def _launch_next_task(self, executor: Executor) -> "None | Future[_OK | _ERR]":
        pass

    def _done(self) -> bool:
        return isinstance(self._status, (JobCanceled, JobFinished))

    def add_done_callback(self, callback: Callable[["JobCanceled | JobFinished[_OK, _ERR]"], None]):
        run_immediately_arg: "None | JobCanceled | JobFinished[_OK, _ERR]"
        with self.job_lock:
            if isinstance(self._status, (JobCanceled, Job)):
                run_immediately_arg = self._status
            else:
                self.on_complete_callbacks.append(callback)
                run_immediately_arg = None
        if run_immediately_arg:
            callback(run_immediately_arg)

    def cancel(self) -> bool:
        callbacks_to_call: List[Callable[["JobCanceled | JobFinished[_OK, _ERR]"], None]]
        with self.job_lock:
            if self._done():
                return False
            self._status = status = JobCanceled("Job cancelled by user")
            callbacks_to_call = self.on_complete_callbacks[:]
        for callback in callbacks_to_call:
            callback(status)
        return True

class SimpleJob(Job[_OK, _ERR]):
    def __init__(
        self,
        name: str,
        target: Callable[_P, "_OK | _ERR"],
        *args: _P.args,
        **kwargs: _P.kwargs,
    ):
        super().__init__(name=name, num_args=1)
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self._status: "JobFinished[_OK, _ERR] | JobIsPending | JobIsRunning | JobCanceled" = JobIsPending()

    def _launch_next_task(self, executor: Executor) -> "None | Future[_OK | _ERR]":
        with self.job_lock:
            if not isinstance(self._status, JobIsPending):
                return None
            self._status = JobIsRunning(num_completed_steps=0, num_dispatched_steps=1)

        future = executor.submit(self.target, *self.args, **self.kwargs)

        def step_done_callback(future: Future["_OK | _ERR"]): # FIXME
            callbacks_to_call: List[Callable[["JobCanceled | JobFinished[_OK, _ERR]"], None]]
            with self.job_lock:
                if self._done():
                    return
                if future.cancelled():
                    self._status = status = JobCanceled("Job cancelled on executor")
                else:
                    self._status = status = JobFinished[_OK, _ERR](future.result())
                callbacks_to_call = self.on_complete_callbacks[:]
            for callback in callbacks_to_call:
                callback(status)

        future.add_done_callback(step_done_callback)
        return future


class IteratingJob(Job[None, _ERR], Generic[_IN, _ERR]):
    def __init__(
        self,
        *,
        name: str,
        target: Callable[[_IN], "None | _ERR"],
        on_progress: "JobProgressCallback" = lambda job_id, step_index: None,
        args: Iterable[_IN],
        num_args: "int | None" = None,
    ):
        super().__init__(
            name=name,
            num_args=num_args or (len(args) if isinstance(args, Sized) else None)
        )
        self.target = target
        self.on_progress = on_progress
        self.args: PeekableIterator[_IN] = PeekableIterator(args)

    def _launch_next_task(self, executor: Executor) -> "Future[None | _ERR] | None":
        with self.job_lock:
            if isinstance(self._status, (JobCanceled, JobFinished)):
                return None
            step_arg = self.args.get_next()
            if isinstance(self._status, JobIsPending):
                self._status = JobIsRunning(num_completed_steps=0, num_dispatched_steps=1)
            else:
                self._status.num_dispatched_steps += (0 if isinstance(step_arg, Empty) else 1)
        if isinstance(step_arg, Empty):
            return None

        def step_done_callback(future: Future["None | _ERR"]): # FIXME
            on_complete_callbacks: List[Callable[["JobCanceled | JobFinished[None, _ERR]"], None]] = []
            with self.job_lock:
                if isinstance(self._status, (JobCanceled, JobFinished)):
                    return
                assert not isinstance(self._status, JobIsPending)
                step_index = self._status.num_completed_steps
                self._status.num_completed_steps += 1
                result = future.result()
                if isinstance(result, Exception):
                    self._status = JobCanceled(f"Cancelled due to exception: {result}")
                    on_complete_callbacks = self.on_complete_callbacks[:]
                elif not self.args.has_next() and self._status.num_dispatched_steps == self._status.num_completed_steps:
                    self._status = JobFinished(None)
                    on_complete_callbacks = self.on_complete_callbacks[:]
                status = self._status
            if self.on_progress:
                self.on_progress(job_id=self.uuid, step_index=step_index)
            if not isinstance(status, JobIsRunning):
                for callback in on_complete_callbacks:
                    callback(status)

        future = executor.submit(self.target, step_arg)
        future.add_done_callback(step_done_callback)
        return future



_T = TypeVar("_T")

class _Task(Generic[_T]):
    def __init__(self, *, target: Callable[[], _T]) -> None:
        self.target = target
        self.creation_time = time.time()
        self.future: Future[_T] = Future()
        super().__init__()

    def __lt__(self, other: object) -> bool:
        if isinstance(other, _Shutdown):
            return False
        if isinstance(other, Job):
            return True
        assert isinstance(other, _Task)
        return self.creation_time < other.creation_time #FIXME: maybe prioritize most recent?


class _Shutdown:
    def __init__(self, wait: bool) -> None:
        self.wait = wait
        super().__init__()

    def __lt__(self, other: object) -> bool:
        return True

class JobFuture(_Task[_T]):
    def __init__(
        self,
        name: str,
        target: Callable[_P, _T],
        *args: _P.args,
        **kwargs: _P.kwargs,
    ):
        self.name = name
        super().__init__(target=functools.partial(target, *args, **kwargs))

    def __lt__(self, other: object) -> bool:
        return False

    def add_done_callback(self, callback: Callable[["_T | Empty"], None]):
        self.future.add_done_callback(lambda f: callback(Empty() if f.cancelled() else f.result()))


class PriorityExecutor(Executor):
    def __init__(self, executor: Executor, max_active_job_steps: int) -> None:
        self._job_step_semaphore = threading.Semaphore(max_active_job_steps)
        self._status_lock = threading.Lock()
        self._status: Literal["ready", "shutting_down"] = "ready"
        self._wrapped_executor: Executor = executor
        self._work_queue: "queue.PriorityQueue[Job[Any, Any] | _Task[Any] | _Shutdown]" = queue.PriorityQueue()

        self._enqueueing_thread = threading.Thread(group=None, target=self._enqueueing_target)
        self._enqueueing_thread.start()
        super().__init__()

    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None: #FIXME: use cancel_futures
        with self._status_lock:
            if self._status != "ready":
                return
            self._status = "shutting_down"
        self._work_queue.put(_Shutdown(wait))
        self._job_step_semaphore.release() #FIXME: is this enough?
        self._enqueueing_thread.join()
        self._wrapped_executor.shutdown(wait)

    def __del__(self):
        self.shutdown(wait=True)

    def submit_job(self, job: Job[Any, Any]):
        with self._status_lock:
            if self._status != "ready":
                raise Exception("Executor is shutting down")
            self._work_queue.put(job)

    def submit(self, fn: Callable[_P, _T], *args: _P.args, **kwargs: _P.kwargs) -> Future[_T]:
        with self._status_lock:
            if self._status != "ready":
                raise Exception("Executor is shutting down")
            task = _Task(target=functools.partial(fn, *args, **kwargs))
            self._work_queue.put(task)
            return task.future

    def _cancel_all_remaining_work(self):
        while True:
            try:
                work = self._work_queue.get_nowait()
                if isinstance(work, Job):
                    _ = work.cancel()
                elif isinstance(work, _Task):
                    _ = work.future.cancel()
            except queue.Empty:
                return

    def _submit_all_remaining_work(self):
        while True:
            try:
                work = self._work_queue.get_nowait()
                if isinstance(work, Job):
                    while work._launch_next_task(self._wrapped_executor):
                        pass
                elif isinstance(work, _Task):
                    _ = work.future.cancel()
            except queue.Empty:
                return

    def _launch_standalone_task(self, task: _Task[Any]):
        if not task.future.set_running_or_notify_cancel():
            return

        inner_future = self._wrapped_executor.submit(task.target)
        # print(f"%%%%% Job Executor launched a NORMAL TASK")

        def update_task_future(fut: Future[Any]):
            exception = fut.exception()
            if exception:
                task.future.set_exception(exception)
            else:
                task.future.set_result(fut.result())

        inner_future.add_done_callback(update_task_future)

    def _enqueueing_target(self):
        num_launched_tasks = 0

        while True:
            work = self._work_queue.get()

            if isinstance(work, _Shutdown):
                with self._status_lock:
                    self._status = "shutting_down"
                if work.wait:
                    self._submit_all_remaining_work()
                else:
                    self._cancel_all_remaining_work()
                return

            if isinstance(work, _Task):
                self._launch_standalone_task(work)
                continue

            job = work
            _ = self._job_step_semaphore.acquire()
            step_future = job._launch_next_task(self._wrapped_executor)
            if step_future:
                num_launched_tasks += 1
                # print(f"%%%%%% JobExecutor launched another JOB step (total: {num_launched_tasks})")
                step_future.add_done_callback(lambda _: self._job_step_semaphore.release())
                self._work_queue.put(job)
            else:
                self._job_step_semaphore.release()
