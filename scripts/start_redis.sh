#!/usr/bin/bash

set -uxe

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

redis-server \
    --port 0 \
    --unixsocket $REDIS_UNIX_SOCKET_PATH \
    --unixsocketperm 777 \
    --daemonize no \
    --maxmemory-policy allkeys-lru \
    --maxmemory 10gb \
    --dir $SCRIPT_DIR/tests/tmp \
    "$@"
