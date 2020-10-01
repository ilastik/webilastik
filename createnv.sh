#!/bin/bash

set -e
set -x
set -u

ENVIRONMENT_NAME="webilastik"

conda create -n ${ENVIRONMENT_NAME} -c ilastik-forge -c conda-forge \
    numpy \
    fastfilters \
    fs \
    vigra \
    scikit-image \
    scikit-learn \
    h5py \
    typing_extensions \
    flask \
    flask-cors \
    requests \
    ipython \

export YELLOW="\e[33m"
export RED="\e[31m"
export END_COLOR="\e[0m"

echo -e "${YELLOW}Make sure you have the ${RED}dev${YELLOW} branch of ${RED}ndstructs${YELLOW} in your PYTHONPATH${END_COLOR}"

#git clone https://github.com/ilastik/ndstructs -b dev

#BASE_ENVIRONMENT="$(conda info | grep "base environment" | awk '{print $4}')"
#ENV_PATH="${BASE_ENVIRONMENT/envs/${ENVIRONMENT_NAME}}"
#PYTHON="${ENV_PATH}/bin/python"

#$PYTHON -m pip install -e ndstructs/
