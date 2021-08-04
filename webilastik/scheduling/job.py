from __future__ import annotations

from abc import ABC
from concurrent.futures import Future, CancelledError
from typing import Any, Callable, Generic, Optional, Protocol, TypeVar, Iterable, Hashable, Union
import enum
from webilastik.scheduling.hashing_executor import HashingExecutor

IN = TypeVar("IN", bound=Hashable)
OUT = TypeVar("OUT")

class StepCompleteCallback(Protocol):
    def __call__(self, step_index: int) -> None:
        ...

class JobStatus(enum.IntEnum):
    RUNNING = 1
    CANCELLED = 2
    SUCCESS = 3

class Job(Generic[IN, OUT]):
    def __init__(
        self,
        *,
        name: str,
        target: Callable[[IN], OUT],
        steps: Iterable[IN],
        executor: HashingExecutor,
        step_complete_callback: Optional[StepCompleteCallback] = None,
        job_complete_callback: Optional[Callable[["Job[Any, Any]"], None]] = None,
    ):
        self.name = name
        self.status : Union[JobStatus | BaseException] = JobStatus.RUNNING
        self.step_futures = [executor.submit(target, step) for step in steps]
        self.finished_step_count = 0
        self.step_complete_callback = step_complete_callback
        self.job_complete_callback = job_complete_callback

        def done_callback(future: Future[OUT]):
            self.finished_step_count += 1
            if self.status == JobStatus.RUNNING:
                try:
                    future.exception()
                except CancelledError as e:
                    self.status = JobStatus.CANCELLED
                except BaseException as e:
                    self.status = e
                else:
                    if self.finished_step_count == len(self.step_futures):
                        self.status = JobStatus.SUCCESS
            if step_complete_callback:
                step_complete_callback(self.finished_step_count - 1)
            if job_complete_callback and self.finished_step_count == len(self.step_futures):
                job_complete_callback(self)

        for step_future in self.step_futures:
            step_future.add_done_callback(done_callback)
        print(f"Schedulling {self.name} scheduled {len(self.step_futures)} steps")

    def cancel(self):
        cancelled_steps = 0
        for fut in self.step_futures:
            cancelled_steps += fut.cancel()
        print(f"Cancelling {self.name} cancelled {cancelled_steps} steps")
