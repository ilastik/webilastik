from dataclasses import dataclass
from typing import List, Literal, NewType, Optional
from typing_extensions import TypeAlias

from pathlib import Path

CpuBind: TypeAlias = Literal["quiet", "verbose", "none"]

class SrunCommand:
    def __init__(
        self,
        *,
        ntasks: int,
        cpus_per_task: int,
        overlap: bool,
        cpu_bind: CpuBind,
    ):
        super().__init__()
        self.ntasks = ntasks
        self.cpus_per_task = cpus_per_task
        self.overlap = overlap
        self.cpu_bind = cpu_bind

    def to_process_launcher_prefix(self) -> str:
        return " ".join([
            f"srun -n {self.ntasks}",
                f"--cpus-per-task {self.cpus_per_task}",
                ('--overlap' if self.overlap else ''),
                f"--cpu-bind {self.cpu_bind}",
        ])

class InsuficientResourcesException(Exception):
    pass

class SingleNodeAllocation:
    def __init__(self, cpus_in_node: int, overlap: bool = False) -> None:
        super().__init__()
        self.remaining_cpus = cpus_in_node
        self.overlap = overlap

    def make_srun_command(
        self,
        *,
        ntasks: int,
        cpus_per_task: int,
        overlap: bool,
        cpu_bind: CpuBind,
        command: str,
    ) -> "SrunCommand | Exception":
        total_requested_cpus = ntasks * cpus_per_task
        if total_requested_cpus > self.remaining_cpus:
            return InsuficientResourcesException(
                f"Insufficient cpus on node: {self.remaining_cpus}. Requested {total_requested_cpus} cpus"
            )
        self.remaining_cpus -= total_requested_cpus
        return SrunCommand(
            ntasks=ntasks,
            cpus_per_task=cpus_per_task,
            overlap=overlap,
            cpu_bind=cpu_bind,
        )

    # def consume_all_with_single_task(self) -> SrunCommand:
    #     return SrunCommand(
    #         ntasks=1, cpus_per_task=self.remaining_cpus, overlap=
    #     )

    def consume_remaining(
        self,
        *,
        ntasks: Optional[int],
        cpus_per_task: int,
        overlap: bool,
        cpu_bind: CpuBind,
        command: str,
    ) -> "SrunCommand | InsuficientResourcesException":
        ntasks = ntasks or self.remaining_cpus // cpus_per_task
        required_cpus = ntasks * cpus_per_task
        if required_cpus > self.remaining_cpus:
            return InsuficientResourcesException(
                f"Remaining CPUs in node {self.remaining_cpus} not enough for allocation of {required_cpus} CPUs"
            )
        return SrunCommand(ntasks=ntasks, cpus_per_task=cpus_per_task, overlap=overlap, cpu_bind=cpu_bind)



class SlurmAllocation:
    def __init__(self, *, nodes: int, ntasks: int, cpus_in_node: int) -> None:
        super().__init__()
        self.nodes = nodes
        self.remaining_tasks = ntasks
        self.cpus_in_node = cpus_in_node

    def make_srun_command(
        self,
        *,
        ntasks: int,
        cpus_per_task: int,
        cpu_bind: CpuBind,
        overlap: bool,
    ) -> "SrunCommand | InsuficientResourcesException":
        if ntasks > self.remaining_tasks:
            return InsuficientResourcesException(f"Not enough tasks left")
        if cpus_per_task > self.cpus_in_node:
            return InsuficientResourcesException(f"Not enough CPUs to run t")

        self.remaining_tasks -= ntasks
        return SrunCommand(
            ntasks=ntasks,
            cpus_per_task=cpus_per_task,
            cpu_bind=cpu_bind,
            overlap=overlap,
        )

    def consume_node_allocation(self) -> SingleNodeAllocation:
        return SingleNodeAllocation(
            cpus_in_node=self.cpus_in_node,
        )

    def consume_remaining(
        self,
        *,
        ntasks: int,
        cpus_per_task: int,
        overlap: bool,
        cpu_bind: CpuBind,
        command: str,
    ):
        pass
