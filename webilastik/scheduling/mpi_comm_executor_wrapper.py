from concurrent.futures import Executor, Future
from typing import TypeVar, Callable, Iterable, Any, Iterator, Type
from types import TracebackType
from typing_extensions import ParamSpec, Self
from mpi4py.MPI import COMM_WORLD
import mpi4py.futures

_P = ParamSpec("_P")
_T = TypeVar("_T")

class MPICommExecutorWrapper(Executor):
    def __init__(self) -> None:
        super().__init__()
        executor = mpi4py.futures.MPICommExecutor(COMM_WORLD, root=0).__enter__()
        if executor is None:
            exit(0)
        self._executor = executor
        self._has_shut_down = False

    def submit(self, fn: Callable[_P, _T], *args: _P.args, **kwargs: _P.kwargs) -> Future[_T]:
        return self._executor.submit(fn, *args, **kwargs)

    def map(self, fn: Callable[..., _T], *iterables: Iterable[Any], timeout: "float | None" = None, chunksize: int = 1) -> Iterator[_T]:
        return self._executor.map(fn, *iterables, timeout=timeout, chunksize=chunksize)

    def __enter__(self: Self) -> Self: #pyright: ignore [reportMissingSuperCall]
        return self

    def __exit__( #pyright: ignore [reportMissingSuperCall]
        self, exc_type: "Type[BaseException] | None", exc_val: "BaseException | None", exc_tb: "TracebackType | None"
    ) -> "bool | None":
        if not self._has_shut_down:
            self._has_shut_down = True
            return self._executor.__exit__(exc_type, exc_val, exc_tb)
        return None

    def shutdown(self, wait: bool = True) -> None:
        _ = self.__exit__(None, None, None)
        return None