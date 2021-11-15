# pyright: strict

from concurrent import futures
from typing import Awaitable, Hashable, Iterator, Optional, TypeVar, Callable
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import asyncio
import time


IN = TypeVar("IN", bound=Hashable)
OUT = TypeVar("OUT")

# Does not inherit from concurrent.futures.Executor because the typing there is looser (too many Any's)
class HashingExecutor:
    """Exports the outputs of an operator created by an upstream applet."""
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or max(1, multiprocessing.cpu_count() - 1)
        self._executors = [ProcessPoolExecutor(max_workers=1) for _ in range(self.max_workers)]

    def _get_executor(self, arg: Hashable) -> ProcessPoolExecutor:
        return self._executors[hash(arg) % len(self._executors)]

    def __del__(self):
        self.shutdown()

    def async_submit(self, target: Callable[[IN], OUT], arg: IN) -> Awaitable[OUT]:
        loop = asyncio.get_event_loop()
        executor = self._get_executor(arg)
        return loop.run_in_executor(executor, target, arg)

    def shutdown(self, wait: bool = True):
        for idx, executor in enumerate(self._executors):
            print(f"===> Shutting down executor {idx} from {self}")
            executor.shutdown(wait)

    def submit(self, fn: Callable[[IN], OUT], arg: IN) -> futures.Future[OUT]:
        return self._get_executor(arg).submit(fn, arg)

    def map(self, fn: Callable[[IN], OUT], *args: IN, timeout: Optional[float] = None, chunksize: int = 1) -> Iterator[OUT]:
        # whole method copied from futures.Executor
        if timeout is not None:
            end_time = timeout + time.monotonic()

        fs = [self.submit(fn, arg) for arg in args]

        def result_iterator():
            try:
                fs.reverse()
                while fs:
                    if timeout is None:
                        yield fs.pop().result()
                    else:
                        yield fs.pop().result(end_time - time.monotonic())
            finally:
                for future in fs:
                    _ = future.cancel()
        return result_iterator()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb): # type: ignore
        self.shutdown(wait=True)
        return False