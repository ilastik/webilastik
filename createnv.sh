#!/bin/bash

set -e
set -x

conda create -n webilastik -c ilastik-forge -c conda-forge \
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
    #dask \
    #dask-image \
