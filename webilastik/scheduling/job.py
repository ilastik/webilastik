from typing import Callable, Generic, Iterable, Iterator, Literal, Protocol, Any, Sized, TypeVar
from collections.abc import Sized
import threading
from concurrent.futures import Future, Executor
import uuid
from enum import Enum

from ndstructs.utils.json_serializable import JsonObject

IN = TypeVar("IN", covariant=True)

class JobProgressCallback(Protocol):
    def __call__(self, job_id: uuid.UUID, step_index: int) -> Any:
        ...

class JobCompletedCallback(Protocol):
    def __call__(self, job_id: uuid.UUID) -> Any:
        ...

class Job(Generic[IN], Future[None]):
    def __init__(
        self,
        *,
        name: str,
        target: Callable[[IN], None],
        args: Iterable[IN],
        num_args: "int | None" = None,
        on_progress: "JobProgressCallback | None" = None,
    ):
        self.name = name
        self.target = target
        self.args = (a for a in args)
        self.num_args: "int | None" = num_args or (len(args) if isinstance(args, Sized) else None)
        self.on_progress = on_progress

        self.uuid: uuid.UUID = uuid.uuid4()
        self.num_completed_steps = 0
        self.num_dispatched_steps = 0
        self.fully_dispatched = False
        self.lock = threading.Lock()

        super().__init__()

    def launch_next_step(self, executor: Executor) -> "Future[None] | BaseException | None":
        def done_callback(future: Future[Any]): # FIXME
            with self.lock:
                self.num_completed_steps += 1
                if self.done():
                    return
                if future.cancelled():
                    _ = self.cancel()
                    return
                if future.exception():
                    self.set_exception(future.exception())
                    return
                if self.fully_dispatched and self.num_completed_steps == self.num_dispatched_steps:
                    self.set_result(None)

        with self.lock:
            exception = self.exception()
            if exception:
                return exception
            if self.done():
                return None
            if not self.running(): #not done nor running -> pending
                _ = self.set_running_or_notify_cancel()

            try:
                future = executor.submit(self.target, next(self.args))
                future.add_done_callback(done_callback)
                self.num_dispatched_steps += 1
                on_progress = self.on_progress
                if on_progress:
                    future.add_done_callback(lambda _: on_progress(self.uuid, self.num_completed_steps))
            except StopIteration:
                self.fully_dispatched = True
                if self.num_args is None:
                    self.num_args = self.num_dispatched_steps
                return None

    def status(self) -> Literal["pending", "running", "cancelled", "failed", "success"]:
        with self.lock:
            if self.cancelled():
                return "cancelled"
            if self.exception():
                return "failed"
            if self.done():
                return "success"
            if self.running():
                return "running"
            return "pending"

    def to_json_value(self) -> JsonObject:
        exception = self.exception()
        with self.lock:
            return {
                "name": self.name,
                "num_args": self.num_args,
                "uuid": str(self.uuid),
                "status": self.status(),
                "num_completed_steps": self.num_completed_steps,
                "error_message": exception and str(exception)
            }

