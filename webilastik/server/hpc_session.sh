#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

srun --ntasks 1 "${DIR}/hpc_session.py" "$@"
