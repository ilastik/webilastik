from concurrent.futures import ProcessPoolExecutor
import time
import os
from typing import Any
import uuid
from tests import run_all_tests

from webilastik.scheduling.job import Job, PriorityExecutor


def green(message: str):
    print(f"\033[32m {message}\033[0m")

def blue(message: str):
    print(f"\033[34m {message}\033[0m")

def yellow(message: str):
    print(f"\033[33m {message}\033[0m")


def do_some_work(a: int):
    time.sleep(a)
    yellow(f"||||||| Worker [{os.getpid()}] finished work")

def test_priority_executor():
    wait_time_per_task = 1
    num_workers = 5
    num_job_steps = num_workers * 2
    num_standalone_tasks = num_workers
    expected_execution_time = ((num_job_steps + num_standalone_tasks) / num_workers) * wait_time_per_task


    def on_job_finished(job_id: uuid.UUID, result: Any):
        total_execution_time = time.time() - start_time
        print(f"Total execution time: {total_execution_time}")
        print(f"Expected execution time: {expected_execution_time}")
        assert total_execution_time - expected_execution_time <= 1

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        priority_executor = PriorityExecutor(executor=executor, max_active_job_steps=num_workers)

        job = Job(
            target=do_some_work,
            args=[wait_time_per_task] * num_job_steps,
            name="My Job",
            on_progress=lambda job_id, step_index: blue(f"Step {step_index} of job {job_id} is complete!"),
            on_success=on_job_finished,
        )

        start_time = time.time()
        priority_executor.submit_job(job)

        for _ in range(num_standalone_tasks):
            f = priority_executor.submit(do_some_work, 1)
            f.add_done_callback(lambda _: green(f"Normal task completed"))

        time.sleep(expected_execution_time + 2)
        priority_executor.shutdown(wait=True)

if __name__ == "__main__":
    import sys
    run_all_tests(sys.modules[__name__])