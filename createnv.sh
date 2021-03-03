#!/bin/bash

set -e
set -x
set -u

ENVIRONMENT_NAME="${ENVIRONMENT_NAME:-webilastik}"
NDSTRUCTS_URL="${NDSTRUCTS_URL:-https://github.com/ilastik/ndstructs.git}"

conda create -n ${ENVIRONMENT_NAME} -c ilastik-forge -c conda-forge python=3.7 \
    numpy \
    fastfilters \
    fs \
    vigra \
    scikit-image \
    scikit-learn \
    h5py \
    typing_extensions \
    aiohttp \
    requests \
    pytest \
    python-jose \

BASE_ENVIRONMENT="$(conda info | grep "base environment" | awk '{print $4}')"
ENV_PATH="${BASE_ENVIRONMENT}/envs/${ENVIRONMENT_NAME}"
PYTHON="${ENV_PATH}/bin/python"

$PYTHON -m pip install pyunicore

git clone "$NDSTRUCTS_URL" -b dev ndstructs/
$PYTHON -m pip install -e ndstructs/
