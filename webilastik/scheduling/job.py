#pyright: strict
#pyright: reportPrivateUsage=false

import queue
from typing import Callable, Generic, Iterable, Literal, Protocol, Any, TypeVar
from typing_extensions import ParamSpec
from collections.abc import Sized
import threading
import uuid
import time
from concurrent.futures import Executor, Future
import functools

from webilastik.utility import PeekableIterator

IN = TypeVar("IN", covariant=True)
OUT = TypeVar("OUT")

JOB_STEP_RESULT = TypeVar("JOB_STEP_RESULT", contravariant=True)

JobStatus = Literal["pending", "running", "cancelled", "completed"]

class JobProgressCallback(Protocol[JOB_STEP_RESULT]):
    def __call__(
        self, *, job_id: uuid.UUID, job_status: JobStatus, step_index: int, step_result: JOB_STEP_RESULT
    ) -> Any:
        ...


class Job(Generic[OUT]):
    def __init__(
        self,
        *,
        name: str,
        target: Callable[[IN], OUT],
        on_progress: "JobProgressCallback[OUT] | None" = None,
        args: Iterable[IN],
        num_args: "int | None" = None,
    ):
        super().__init__()
        self.creation_time = time.time()
        self.name = name
        self.target = target
        self.on_progress: "JobProgressCallback[OUT] | None" = on_progress
        self.num_args: "int | None" = num_args or (len(args) if isinstance(args, Sized) else None)
        self.args: PeekableIterator[IN] = PeekableIterator(args)

        self.uuid: uuid.UUID = uuid.uuid4()
        self.num_completed_steps = 0
        self.num_dispatched_steps = 0
        self.job_lock = threading.Lock()
        self._status: JobStatus = "pending"

    def _done(self) -> bool:
        return self._status == "cancelled" or self._status == "completed"

    def _launch_next_task(self, executor: Executor) -> "Future[OUT] | None":
        if self._done():
            return None
        if not self.args.has_next():
            self.num_args = self.num_dispatched_steps #FIXME
            return None
        step_arg = self.args.get_next()
        if self._status == "pending":
            self._status = "running"
        step_index = self.num_dispatched_steps
        self.num_dispatched_steps += 1

        def step_done_callback(future: Future[Any]): # FIXME
            with self.job_lock:
                self.num_completed_steps += 1
                if self._status == "cancelled":
                    return
                if not self.args.has_next() and self.num_dispatched_steps == self.num_completed_steps:
                    self._status = "completed"
                job_status = self._status
            if self.on_progress:
                self.on_progress(job_id=self.uuid, job_status=job_status, step_index=step_index, step_result=future.result())

        future = executor.submit(self.target, step_arg)
        future.add_done_callback(step_done_callback)
        return future

    def cancel(self) -> bool:
        with self.job_lock:
            if self._done():
                return False
            self._status = "cancelled"
        return True

    def __lt__(self, other: object) -> bool:
        if isinstance(other, (_Shutdown, _Task)):
            return False
        assert isinstance(other, Job)
        return self.creation_time < other.creation_time


_P = ParamSpec("_P")
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


class PriorityExecutor(Executor):
    def __init__(self, executor: Executor, max_active_job_steps: int) -> None:
        self._job_step_semaphore = threading.Semaphore(max_active_job_steps)
        self._status_lock = threading.Lock()
        self._status: Literal["ready", "shutting_down"] = "ready"
        self._wrapped_executor: Executor = executor
        self._work_queue: "queue.PriorityQueue[Job[Any] | _Task[Any] | _Shutdown]" = queue.PriorityQueue()

        self._enqueueing_thread = threading.Thread(group=None, target=self._enqueueing_target)
        self._enqueueing_thread.start()
        super().__init__()

    def shutdown(self, wait: bool = True) -> None:
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

    def submit_job(self, job: Job[Any]):
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