#!/bin/bash
set -u
set -e
set -x
set -o pipefail


#Params:
MASTER_USER="${MASTER_USER}"
MASTER_HOST="${MASTER_HOST}"
SOCKET_PATH_AT_MASTER="${SOCKET_PATH_AT_MASTER}"
SOCKET_PATH_AT_SESSION="${SOCKET_PATH_AT_SESSION}"
PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-python}"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
WEBILASTIK_ROOT=$(readlink -f "${DIR}/../../")

function errcho(){
    echo "$@" 1>&2
}

TUNNEL_CONTROL_SOCKET="${SOCKET_PATH_AT_SESSION}.tunnel_control"

function close_tunnel(){
    if [ -e "${TUNNEL_CONTROL_SOCKET}" ]; then
        errcho "--> Closing tunnel"
        ssh -S "${TUNNEL_CONTROL_SOCKET}" -O exit "${MASTER_USER}@${MASTER_HOST}"
        rm -f "${TUNNEL_CONTROL_SOCKET}" "${SOCKET_PATH_AT_SESSION}"
    fi
}

trap close_tunnel SIGINT

errcho "--> Removing leftover sockets, if any..."
rm -fv "${SOCKET_PATH_AT_SESSION}"
ssh "${MASTER_USER}@${MASTER_HOST}" -- rm -fv "$SOCKET_PATH_AT_MASTER"

errcho "--> Stabilishing reverse-tunnel from master to session"
ssh -M -S "${TUNNEL_CONTROL_SOCKET}" -fnNT -R "${SOCKET_PATH_AT_MASTER}:${SOCKET_PATH_AT_SESSION}" "${MASTER_USER}@${MASTER_HOST}"

"${PYTHON_EXECUTABLE}"  "${WEBILASTIK_ROOT}/webilastik/ui/workflow/ws_pixel_classification_workflow.py" --unix-socket-path "${SOCKET_PATH_AT_SESSION}"

close_tunnel
