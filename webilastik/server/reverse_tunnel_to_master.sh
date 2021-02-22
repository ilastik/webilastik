#!/bin/bash
set -u
set -e
set -x

MASTER_USER="${MASTER_USER}"
MASTER_IP="${MASTER_IP}"
SOCKET_PATH_AT_MASTER="${SOCKET_PATH_AT_MASTER}"
SOCKET_PATH_AT_WORKER="${SOCKET_PATH_AT_WORKER}"
SOCKET_PATH_AT_WORKER="${SOCKET_PATH_AT_WORKER}"


rm -fv "${SOCKET_PATH_AT_WORKER}"
nc -lkU "${SOCKET_PATH_AT_WORKER}" &

ssh "${MASTER_USER}@${MASTER_IP}" -- rm -fv "$SOCKET_PATH_AT_MASTER"
ssh -R "${SOCKET_PATH_AT_MASTER}:${SOCKET_PATH_AT_WORKER}" "${MASTER_USER}@${MASTER_IP}" -N &
TUNNEL_PID=$!

function cleanup(){
    echo "Killing tunnel process (${TUNNEL_PID})"
    kill -2 $TUNNEL_PID
    #sleep 2
    #kill -9 $TUNNEL_PID
}

trap cleanup SIGINT

PYTHONPATH=. python webilastik/ui/workflow/ws_pixel_classification_workflow.py --unix-socket-path "${SOCKET_PATH_AT_WORKER}"
