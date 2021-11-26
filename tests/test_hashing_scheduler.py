import time

import asyncio
from typing import Any, List


from webilastik.scheduling.hashing_executor import HashingExecutor



def quick_work(a: int):
    time.sleep(1)
    print(f"Quickly {a} slept for 1 second")
    return a

def slow_work(a: int):
    time.sleep(3)

def schedule_some_tasks():
    executor = HashingExecutor(max_workers=2, name="My Executor")

    def on_job_step_completed(job_id: Any, step_index: int):
        print(f"** Job step {step_index} done")

    def on_job_completed(job_id: Any):
        print(f"**** Job completed")

    print("===>>> Submitting a job")
    _ = executor.submit_job(
        target=slow_work,
        args=range(10),
        on_progress=on_job_step_completed,
        on_complete=on_job_completed,
    )

    print("===>>> Submitting some quick tasks")
    quick_futures = [executor.submit(quick_work, i) for i in range(10)]

    results = [f.result() for f in quick_futures]

    # results: List[int] = []
    # for f in quick_futures:
    #     results.append(await asyncio.wrap_future(f))
    print(f"These are the results and I think I should be done? {results}")


    executor.shutdown()


# asyncio.run(blas())
schedule_some_tasks()