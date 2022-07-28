#!/usr/bin/bash

set -uxe

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_DIR="$(realpath $SCRIPT_DIR/../..)"

export PYTHONPATH="$PROJECT_DIR"

mpiexec --use-hwthread-cpus -n 8 python $SCRIPT_DIR/test_hashing_mpi_executor.py