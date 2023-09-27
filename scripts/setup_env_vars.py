from pathlib import Path
import os
import argparse

if __name__ == "__main__":
    project_root_path = Path(__file__).parent.parent

    parser = argparse.ArgumentParser()
    _ = parser.add_argument(
        '--cache-implementation',
        choices=["lru_cache", "no_cache", "redis_cache"],
        default="lru_cache"
    )
    _ = parser.add_argument(
        '--executor-implementation',
        choices=["cscs", "dask", "default", "jusuf", "process_pool", "thread_pool"],
        default="default",
    )
    args = parser.parse_args()

    out = f"export PYTHONPATH={project_root_path}"
    out += os.pathsep + str(project_root_path / 'caching' / args.cache_implementation)
    out += os.pathsep + str(project_root_path / 'executor_getters' / args.executor_implementation)
    out += f"\nexport WEBILASTIK_ALLOW_LOCAL_FS=true"

    print(out)

