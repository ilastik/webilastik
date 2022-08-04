#!/bin/bash

set -xeu

#--- Script params -----
# These combined with "set -u" check that all params are set
EBRAINS_USER_ACCESS_TOKEN="${EBRAINS_USER_ACCESS_TOKEN}"
SESSION_ID="${SESSION_ID}"
MODULES_TO_LOAD="${MODULES_TO_LOAD:-}"
CONDA_ENV_DIR="${CONDA_ENV_DIR}"
WEBILASTIK_SOURCE_DIR="${WEBILASTIK_SOURCE_DIR}"
# ----- end script params -----

if [ $SLURM_NTASKS -lt 2 ]; then
    >&2 echo "Need at least 2 tasks to run redis and the worker concurrently. Provided: {$SLURM_NTASKS}"
    exit 1
fi

for MODULE_NAME in $(echo "$MODULES_TO_LOAD" | tr '@' '\n'); do
    module load $MODULE_NAME
done

CPUS_PER_NODE="$(echo $SLURM_JOB_CPUS_PER_NODE | grep -E '^[0-9]+' -o)"
REDIS_CPUS=10 #FIXME: this is probably too much
WEBILASTIK_WORKER_CPUS="$(expr $CPUS_PER_NODE - $REDIS_CPUS)"

export REDIS_UNIX_SOCKET_PATH="$PROJECT/redis-$SESSION_ID.sock"
REDIS_PID_FILE="$PROJECT/redis-$SESSION_ID.pid"
srun -n 1 --overlap -u --cpu_bind=none --cpus-per-task $REDIS_CPUS\
    $CONDA_ENV_DIR/bin/redis-server \
    --pidfile $REDIS_PID_FILE \
    --unixsocket $REDIS_UNIX_SOCKET_PATH \
    --unixsocketperm 777 \
    --port 0 \
    --daemonize no \
    --maxmemory-policy allkeys-lru \
    --maxmemory 100gb \
    --appendonly no \
    --save "" \
    --dir $PROJECT \
    &

export PYTHONPATH="${WEBILASTIK_SOURCE_DIR}:${WEBILASTIK_SOURCE_DIR}/executor_getters/default/:${WEBILASTIK_SOURCE_DIR}/caching/redis_cache/"
srun -n 1 --overlap -u --cpus-per-task $WEBILASTIK_WORKER_CPUS\
    "$CONDA_ENV_DIR/bin/python" ${WEBILASTIK_SOURCE_DIR}/webilastik/ui/workflow/ws_pixel_classification_workflow.py \
    --ebrains-user-access-token=$EBRAINS_USER_ACCESS_TOKEN \
    --listen-socket="$PROJECT/to-master-$SESSION_ID" \
    tunnel \
    --remote-username=www-data \
    --remote-host=app.ilastik.org \
    --remote-unix-socket="/tmp/to-session-$SESSION_ID" \

kill -2 $(cat $REDIS_PID_FILE)

sleep 2