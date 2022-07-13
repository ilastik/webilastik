#!/usr/bin/bash

set -uxe

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_DIR="$(realpath $SCRIPT_DIR/..)"


EXECUTOR_GETTER_IMPL="$PROJECT_DIR/executor_getters/default/"
# EXECUTOR_GETTER_IMPL="$PROJECT_DIR/executor_getters/process_pool/"
# EXECUTOR_GETTER_IMPL="$PROJECT_DIR/executor_getters/thread_pool/"

CACHE_IMPL_DIR="$PROJECT_DIR/caching/redis_cache/"
# CACHE_IMPL_DIR="$PROJECT_DIR/caching/no_cache/"
# CACHE_IMPL_DIR="$PROJECT_DIR/caching/lru_cache/"

if echo "$CACHE_IMPL_DIR" | grep "redis_cache"; then
    export REDIS_UNIX_SOCKET_PATH=/var/run/redis/redis-server.sock #adjust as necessary if using redis cache
    echo -e "FLUSHDB\nQUIT\n" | redis-cli
fi

export PYTHONPATH="${PROJECT_DIR}:${PROJECT_DIR}/ndstructs/:${CACHE_IMPL_DIR}:${EXECUTOR_GETTER_IMPL}${PYTHONPATH+:$PYTHONPATH}"

mpiexec --use-hwthread-cpus python "${PROJECT_DIR}/benchmarks/pixel_classification_benchmark.py" --executor HashingMpiExecutor  --datasource brain

