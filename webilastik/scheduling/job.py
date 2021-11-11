from __future__ import annotations

from concurrent.futures import Future, CancelledError
from typing import Callable, Generic, Optional, TypeVar, Iterable, Hashable, Union
from typing_extensions import Protocol
import enum
import uuid

from ndstructs.utils.json_serializable import JsonObject
from webilastik.scheduling.hashing_executor import HashingExecutor

IN = TypeVar("IN", bound=Hashable, contravariant=True)
OUT = TypeVar("OUT", covariant=True)

class StepCompleteCallback(Protocol):
    def __call__(self, step_index: int, job_id: uuid.UUID) -> None:
        ...

class JobCompletedCallback(Protocol):
    def __call__(self, job_id: uuid.UUID) -> None:
        ...

class JobStatus(enum.IntEnum):
    RUNNING = 1
    CANCELLED = 2
    SUCCESS = 3
    TIMEOUT = 4

    def to_json_value(self) -> str:
        return self.name

class Job(Generic[IN, OUT]):
    def __init__(
        self,
        *,
        uuid: uuid.UUID,
        name: str,
        target: Callable[[IN], OUT],
        steps: Iterable[IN],
        executor: HashingExecutor,
        step_completed_callback: Optional[StepCompleteCallback] = None,
        job_completed_callback: Optional[JobCompletedCallback] = None,
    ):
        self.uuid = uuid
        self.name = name
        self.status : Union[JobStatus, BaseException] = JobStatus.RUNNING
        self.step_futures = [executor.submit(target, step) for step in steps]
        self.finished_step_count = 0
        self.step_completed_callback = step_completed_callback
        self.job_completed_callback = job_completed_callback

        def done_callback(future: Future[OUT]):
            self.finished_step_count += 1
            if self.status == JobStatus.RUNNING:
                try:
                    exception = future.exception()
                    if exception is not None:
                        raise exception # FIXME: double check this
                except CancelledError as e:
                    self.status = JobStatus.CANCELLED
                except TimeoutError as e:
                    self.status = JobStatus.TIMEOUT
                except BaseException as e:
                    self.status = e
                else:
                    if self.finished_step_count == len(self.step_futures):
                        self.status = JobStatus.SUCCESS
            if step_completed_callback:
                step_completed_callback(self.finished_step_count - 1, self.uuid)
            if job_completed_callback and self.finished_step_count == len(self.step_futures):
                job_completed_callback(self.uuid)

        for step_future in self.step_futures:
            step_future.add_done_callback(done_callback)
        print(f"Schedulling {self.name} scheduled {len(self.step_futures)} steps")

    @property
    def percentage_complete(self) -> float:
        return (self.finished_step_count / len(self.step_futures)) * 100

    @property
    def total_num_steps(self) -> int:
        return len(self.step_futures)

    def cancel(self):
        cancelled_steps = 0
        for fut in self.step_futures:
            cancelled_steps += fut.cancel()
        print(f"Cancelling {self.name} cancelled {cancelled_steps} steps")

    def to_json_value(self) -> JsonObject:
        return {
            "name": self.name,
            "uuid": str(self.uuid),
            "total_num_steps": self.total_num_steps,
            "finished_step_count": self.finished_step_count,
            "status": self.status.to_json_value() if isinstance(self.status, JobStatus) else str(self.status),
        }