#!/usr/bin/bash

set -uxe

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_DIR="$(realpath $SCRIPT_DIR/..)"



PYTHONPATH="$PROJECT_DIR"
PYTHONPATH="$PYTHONPATH:$PROJECT_DIR/caching/redis_cache/"
# PYTHONPATH="$PYTHONPATH:$PROJECT_DIR/caching/lru_cache/"
PYTHONPATH="$PYTHONPATH:$PROJECT_DIR/executor_getters/default/"
# PYTHONPATH="$PYTHONPATH:$PROJECT_DIR/executor_getters/jusuf/"
export PYTHONPATH


if echo "$PYTHONPATH" | grep "redis_cache"; then
    export REDIS_UNIX_SOCKET_PATH=/var/run/redis/redis-server.sock
    echo -e "FLUSHDB\nQUIT\n" | redis-cli
fi


time (
    for i in $(seq 10); do
        # mpiexec --bind-to none --use-hwthread-cpus \
            python "${PROJECT_DIR}/benchmarks/pixel_classification_benchmark.py" \
                --datasource c_cells \
                --num-tiles 10 \

    done
)
