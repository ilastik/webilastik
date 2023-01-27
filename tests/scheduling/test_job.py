from concurrent.futures.thread import ThreadPoolExecutor
import time
from tests import run_all_tests

from webilastik.scheduling.job import PriorityExecutor, Job

def sleeping_target(t: int):
    if t < 0:
        raise ValueError("waaaaaaaaaaaaaaa")
    time.sleep(t)

def test_job():
    executor = ThreadPoolExecutor(max_workers=2)
    priority_executor = PriorityExecutor(executor=executor, max_active_job_steps=1)
    job = Job(
        name="my_test_job",
        target=sleeping_target,
        args=([2] * 10) + [1] + ([2] * 10),
        on_progress=lambda job_id, step_index: print(f"Completed step {step_index} from job {job_id}")
    )
    print(f"Adding job to executor")
    priority_executor.submit_job(job)

    print(f"===>>>> waiting for a while....")
    time.sleep(3)
    # print(f"^^^^^^^^^^^^^^^^^^^^^^^^^ job exception? {job.exception()}")
    priority_executor.shutdown()
    print(f"Called shutdown.")

if __name__ == "__main__":
    import sys
    run_all_tests(sys.modules[__name__])
