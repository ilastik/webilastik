from dataclasses import dataclass
import os
from typing import List, Literal, NewType, Optional
from typing_extensions import TypeAlias
import time

from pathlib import Path

from webilastik.config import GlobalCacheConfig, RedisCacheConfig

class RedisInvocation:
    def __init__(
        self,
        *,
        process_launcher_prefix: Optional[str],
        conda_env_dir: Path,
        working_dir: Path,
        config: RedisCacheConfig,
        maxmemory_gb: int,
    ) -> None:
        super().__init__()
        self.process_launcher_prefix = process_launcher_prefix
        self.conda_env_dir = conda_env_dir
        self.working_dir = working_dir
        self.redis_pid_file = working_dir / "redis.pid"
        self.config = config

        self.args = [
            *(process_launcher_prefix or []),
            f"{conda_env_dir}/bin/redis-server",
            f"--pidfile {self.redis_pid_file}",
            *self.config.to_redis_cmd_line_opts(),
            "--daemonize no",
            "--maxmemory-policy allkeys-lru",
            f"--maxmemory {maxmemory_gb}gb",
            "--appendonly no",
            '--save ""',
            f"--dir {self.working_dir}",
        ]

    def wait_for_pid_file(self, timeout_sec: int = 10) -> "None | Exception":
        wait_time_sec = 1
        while timeout_sec > 0:
            if self.redis_pid_file.exists():
                break
            timeout_sec -= wait_time_sec
            time.sleep(wait_time_sec)
        else:
            return Exception(f"Timed out waiting for {self.redis_pid_file} to show up")

    def kill(self):
        try:
            with open(self.redis_pid_file) as f:
                pid = int(f.read().strip())
                os.kill(pid, 2)
        except:
            pass

class WebilastikWorkflowInvocation:
    def __init__(
        self,
        *,
        process_launcher_prefix: Optional[List[str]],
        project_root_path: Path,
        working_dir: Path,
        conda_env: Path,
        executor_getter: Literal["jusuf", "cscs", "default", "dask"],
        global_cache_config: GlobalCacheConfig,
    ):
        super().__init__()
        self.process_launcher_prefix = process_launcher_prefix
        self.project_root_path = project_root_path
        self.working_dir = working_dir
        self.conda_env = conda_env
        self.executor_getter = executor_getter
        self.global_cache_config = global_cache_config

        self.args = [
            f"{conda_env}/bin/python3",
            f"{project_root_path}/webilastik/ui/workflow/ws_pixel_classification_workflow.py",
        ]

        self.launch_script_lines: List[str] = [
            ev.to_bash_export() for ev in self.global_cache_config.to_env_vars()
        ]
        self.launch_script_lines += [
            f'PYTHONPATH="{self.project_root_path}"',
            f'PYTHONPATH+=":{self.project_root_path}/executor_getters/{self.executor_getter}/"',
            f'PYTHONPATH+=":{self.project_root_path}/caching/{self.global_cache_config.cache_implementation_name}/"',
            'export PYTHONPATH',
            f'{process_launcher_prefix or ""} {self.base_command}'
        ]