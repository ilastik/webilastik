import queue
from typing import Callable, Generic, Iterable, List, Literal, Protocol, Any, Sized, TypeVar
from collections.abc import Sized
import threading
from concurrent.futures import Future, Executor
import uuid

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
        on_complete: "JobCompletedCallback | None" = None,
        args: Iterable[IN],
        num_args: "int | None" = None,
    ):
        super().__init__()
        self.name = name
        self.target = target
        self.on_progress: "JobProgressCallback | None" = on_progress
        if on_complete:
            self.add_done_callback(lambda _: on_complete(self.uuid))
        self.args: PeekableIterator[IN] = PeekableIterator(args)
        self.num_args: "int | None" = num_args or (len(args) if isinstance(args, Sized) else None)

        self.uuid: uuid.UUID = uuid.uuid4()
        self.num_completed_steps = 0
        self.num_dispatched_steps = 0
        self.lock = threading.Lock()

    def _launch_next_step(self, executor: Executor) -> "Future[OUT] | None":
        with self.lock:
            if self.done() or not self.args.has_next():
                return None
            if not self.running():
                _ = self.set_running_or_notify_cancel()
            future = executor.submit(self.target, self.args.get_next())
            self.num_dispatched_steps += 1
            if not self.args.has_next():
                self.num_args = self.num_dispatched_steps #FIXME

        def done_callback(future: Future[Any]): # FIXME
            with self.lock:
                step_index = self.num_completed_steps
                self.num_completed_steps += 1
                if future.cancelled():
                    _ = self.cancel()
                elif future.exception():
                    self.set_exception(future.exception())
                elif not self.args.has_next() and self.num_dispatched_steps == self.num_completed_steps:
                    self.set_result(future.result())
            if self.on_progress:
                self.on_progress(self.uuid, step_index)

        future.add_done_callback(done_callback)
        return future

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

# class JobExecutor:
#     def __init__(self, executor: Executor, concurrent_job_steps: int) -> None:
#         self.executor = executor
#         self.concurrent_job_steps = concurrent_job_steps
#         self.jobs: "List[Job[Any, Any]]" = []
#         self.lock = threading.Lock()

#     def _execute_step(self):
#         with self.lock:
#             if not self.jobs:
#                 return
#             job = self.jobs[0]
#             future = job._launch_next_step(self.executor)
#             if future is None:
#                 _ = self.jobs.pop(0)
#                 future = self.executor.submit(lambda : None)
#         future.add_done_callback(lambda _: self._execute_step())

#     def submit(self, job: Job[Any, Any]):
#         with self.lock:
#             self.jobs.append(job)
#             if len(self.jobs) != 1:
#                 return
#             for i in range(self.concurrent_job_steps):
#                 _ = self.executor.submit(lambda : print(f"SUBMISSION TEST {i}"))
#                 _ = self.executor.submit(self._execute_step)

class _Stop:
    pass

class _StepToken:
    pass

class JobExecutor:
    def __init__(self, executor: Executor, concurrent_job_steps: int) -> None:
        self.executor = executor
        self.concurrent_job_steps = concurrent_job_steps

        self.job_queue: "queue.Queue[Job[Any, Any] | _Stop]" = queue.Queue()
        self.step_token_queue: "queue.Queue[_StepToken | _Stop]" = queue.Queue(maxsize=concurrent_job_steps)
        for _ in range(concurrent_job_steps):
            self.step_token_queue.put(_StepToken())

        self.step_submitter_thread = threading.Thread(
            group=None, target=self._submit_steps, name=f"JobExecutor_submitter_thread"
        )
        self.step_submitter_thread.start()

    def _submit_steps(self):
        while True:
            job = self.job_queue.get()
            if isinstance(job, _Stop):
                return
            while True:
                token = self.step_token_queue.get()
                if isinstance(token, _Stop):
                    return
                future = job._launch_next_step(executor=self.executor)
                if isinstance(future, Future):
                    future.add_done_callback(lambda _: self.step_token_queue.task_done() or self.step_token_queue.put(token))
                else:
                    self.step_token_queue.put(token)
                    break

    def _clear_queues(self):
        queues: "List[queue.Queue[Any]]" = [self.job_queue, self.step_token_queue]
        for q in queues:
            try:
                while True:
                    q.get_nowait()
            except queue.Empty:
                pass

    def shutdown(self):
        self._clear_queues()
        self.job_queue.put(_Stop())
        self.step_token_queue.put(_Stop())
        self.step_submitter_thread.join()

    def __del__(self):
        self.shutdown()

    def submit(self, job: Job[Any, Any]):
        self.job_queue.put(job)