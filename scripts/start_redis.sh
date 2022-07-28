#!/usr/bin/bash

set -uxe

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
TMP_DIR="${SCRIPT_DIR}/../tests/tmp"
REDIS_PID_FILE="${TMP_DIR}/redis.pid"

redis-server \
    --port 0 \
    --unixsocket $REDIS_UNIX_SOCKET_PATH \
    --pidfile $REDIS_PID_FILE \
    --unixsocketperm 777 \
    --daemonize no \
    --maxmemory-policy allkeys-lru \
    --maxmemory 10gb \
    --appendonly no \
    --save "" \
    --dir $TMP_DIR \
    "$@"
