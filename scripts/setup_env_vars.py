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

    cache_impl = args.cache_implementation
    if cache_impl != "default":
        out += os.pathsep + str(project_root_path / 'global_cache_impls' / cache_impl)

    executor_impl = args.executor_implementation
    if executor_impl != "default":
        out += os.pathsep + str(project_root_path / 'executor_getter_impls' / executor_impl)

    out += f"\nexport WEBILASTIK_ALLOW_LOCAL_FS=true"

    print(out)

