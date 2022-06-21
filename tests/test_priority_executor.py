from concurrent.futures import ProcessPoolExecutor
import time

from webilastik.scheduling.job import Job, PriorityExecutor



def do_some_work(a: int):
    time.sleep(a)

def test_priority_executor():
    with ProcessPoolExecutor(max_workers=1) as executor:
        priority_executor = PriorityExecutor(executor=executor, num_concurrent_tasks=1)

        job = Job(
            target=do_some_work,
            args=[1] * 10,
            name="My Job",
            # on_complete=lambda job_id: print(f"Job {job_id} is complete!"),
            on_progress=lambda job_id, step_index: print(f"Step {step_index} of job {job_id} is complete!"),
        )
        priority_executor.submit_job(job)

        time.sleep(2)

        for _ in range(10):
            f = priority_executor.submit(do_some_work, 1)
            f.add_done_callback(lambda _: print(f"Normal task completed"))

        wait = True
        print(f" ====>>>> Shutting down priority executor with wait {wait}")
        priority_executor.shutdown(wait=wait)

if __name__ == "__main__":
    test_priority_executor()