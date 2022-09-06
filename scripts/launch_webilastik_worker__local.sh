#!/usr/bin/bash

set -xeuo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_DIR="$(realpath $SCRIPT_DIR/..)"

# prevent numpy from spawning its own threads
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

# make aiohttp happy with the certs
export SSL_CERT_DIR=/etc/ssl/certs/
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt


SESSION_ID="$(python -c 'import uuid; print(uuid.uuid4())')"
WORKING_DIR="/tmp/session-${SESSION_ID}"

mkdir $WORKING_DIR
cd $WORKING_DIR

unset REDIS_HOST_PORT
export REDIS_UNIX_SOCKET_PATH=/tmp/redis-${SESSION_ID}.socket
export REDIS_PID_FILE=/tmp/redis-${SESSION_ID}.pid

type redis-server
redis-server \
    --pidfile ${REDIS_PID_FILE} \
    --unixsocket ${REDIS_UNIX_SOCKET_PATH} \
    --unixsocketperm 777 \
    --port 0 \
    --daemonize no \
    --maxmemory-policy allkeys-lru \
    --maxmemory 10gb \
    --appendonly no \
    --save "" \
    --dir ${WORKING_DIR} \
    &


NUM_TRIES=10;
while [ ! -e $REDIS_PID_FILE -a $NUM_TRIES -gt 0 ]; do
    echo "Redis not ready yet. Sleeping..."
    NUM_TRIES=$(expr $NUM_TRIES - 1)
    sleep 1
done

if [ $NUM_TRIES -eq 0 ]; then
    echo "Could not start redis"
    exit 1
fi

PYTHONPATH="$PROJECT_DIR"
PYTHONPATH="$PYTHONPATH:$PROJECT_DIR/ndstructs/"
PYTHONPATH="$PYTHONPATH:$PROJECT_DIR/caching/redis_cache/"
PYTHONPATH="$PYTHONPATH:$PROJECT_DIR/executor_getters/default/"
export PYTHONPATH

echo -e "\033[0;32m${SESSION_ID}\033[0m"
echo -n "${SESSION_ID}" | xclip -selection clipboard


# mpiexec --bind-to none --use-hwthread-cpus \
    python ${PROJECT_DIR}/webilastik/ui/workflow/ws_pixel_classification_workflow.py \
        --max-duration-minutes=999999 \
        --listen-socket="/tmp/to-master-$SESSION_ID" \
        --session-url="https://app.ilastik.org/session-${SESSION_ID}" \
        tunnel \
        --remote-username=www-data \
        --remote-host=app.ilastik.org \
        --remote-unix-socket="/tmp/to-session-$SESSION_ID" \
