from concurrent.futures import wait as wait_futures
import time
import functools

from tests import SkipException, run_all_tests

def wait_then_echo(wait_time: int, x: int) -> int:
    time.sleep(wait_time)
    return x

def test_hashing_mpi_executor():
    try:
        from mpi4py import MPI
    except ImportError as e:
        raise SkipException("mpi4py not installed") from e
    if MPI.COMM_WORLD.size <= 1:
        raise SkipException("bad MPI comm size. Maybe this isn't being run with mpiexec ?")

    from webilastik.scheduling.hashing_mpi_executor import HashingMpiExecutor

    executor = HashingMpiExecutor()
    print(f"Created executor!")
    num_workers = executor.num_workers

    # num_workers = 7
    # executor = ProcessPoolExecutor(max_workers=num_workers)

    num_tasks_per_worker = 20
    wait_time = 1
    expected_duration = num_tasks_per_worker * wait_time

    f = functools.partial(wait_then_echo, wait_time)

    t0 = time.time()
    futures = [executor.submit(f, i) for i in range(num_workers * num_tasks_per_worker)]
    # futures = [executor.submit(f, i) for i in range(executor.num_workers * num_tasks_per_worker)]
    _ = wait_futures(futures)
    delta = time.time() - t0

    print(f"All tasks took {delta}s. Expected completion in ~{expected_duration}s")
    # assert delta < expected_duration + 2

    print(f"Shutting down executor...")
    executor.shutdown()
    print(f"DONE Shutting down executor...")


if __name__ == "__main__":
    import sys
    run_all_tests(sys.modules[__name__])