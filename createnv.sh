#!/bin/bash

set -e
set -x
set -u

ENVIRONMENT_NAME="webilastik"

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
    ipython \

BASE_ENVIRONMENT="$(conda info | grep "base environment" | awk '{print $4}')"
ENV_PATH="${BASE_ENVIRONMENT}/envs/${ENVIRONMENT_NAME}"
PYTHON="${ENV_PATH}/bin/python"

$PYTHON -m pip install pydevd uwsgi

git clone https://github.com/ilastik/ndstructs -b dev
$PYTHON -m pip install -e ndstructs/
