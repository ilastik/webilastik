#!/bin/bash
set -u
set -e
set -x
set -o pipefail


# non-dot-slash relative paths can mess up ssh tunneling
ensure_dot_slash_in_relative_path(){
    if echo "$1" | grep -Evq "^(/|./)" ; then
        echo "./$1"
    else
        echo "$1"
    fi
}

#Params:
MASTER_USER="${MASTER_USER}"
MASTER_HOST="${MASTER_HOST}"
SOCKET_PATH_AT_MASTER="${SOCKET_PATH_AT_MASTER}"
SOCKET_PATH_AT_SESSION=$(ensure_dot_slash_in_relative_path "${SOCKET_PATH_AT_SESSION}")
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


export PYTHONPATH="$WEBILASTIK_ROOT"
"${PYTHON_EXECUTABLE}"  "${WEBILASTIK_ROOT}/webilastik/ui/workflow/ws_pixel_classification_workflow.py" --listen-on "unix://${SOCKET_PATH_AT_SESSION}" &

while  ! lsof -U | grep -qEw "${SOCKET_PATH_AT_SESSION}s" ; do
    errcho "----> Waiting for server socket to show up..."
    sleep 2
done
errcho "--> Stabilishing reverse-tunnel from master to session"
ssh -M -S "${TUNNEL_CONTROL_SOCKET}" -fnNT -R "${SOCKET_PATH_AT_MASTER}:${SOCKET_PATH_AT_SESSION}" "${MASTER_USER}@${MASTER_HOST}"

errcho "--> Waiting for server to finish..."
wait

close_tunnel
