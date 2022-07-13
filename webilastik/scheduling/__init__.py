from typing import Literal, Optional, Protocol, TypeVar, Callable
from typing_extensions import ParamSpec
from concurrent.futures import Executor, Future

ExecutorHint = Literal["server_tile_handler", "training", "predicting", "sampling", "any"]

class ExecutorGetter(Protocol):
    def __call__(self, *, hint: ExecutorHint, max_workers: Optional[int] = None) -> Executor:
        ...

_P = ParamSpec("_P")
_T = TypeVar("_T")

class SerialExecutor(Executor):
    def submit(self, fn: Callable[_P, _T], *args: _P.args, **kwargs: _P.kwargs) -> Future[_T]:
        future: Future[_T] = Future()
        _ = future.set_running_or_notify_cancel()
        try:
            future.set_result(fn(*args, **kwargs))
        except Exception as e:
            future.set_exception(e)
        return future