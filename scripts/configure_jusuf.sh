#!/bin/bash

set -eux
set -o pipefail


# HOME=/p/home/jusers/webilastik/jusuf/
HOME=/tmp/blas; mkdir -p $HOME
GIT_REPO_PATH=$HOME/webilastik.git
ENVIRONMENT_YML_PATH=$GIT_REPO_PATH/environment.yml
PIPLESS_ENVIRONMENT_YML_PATH=$HOME/pipless_environment.yml

echo "Cloning webilastik source"
mkdir -p $GIT_REPO_PATH;
cd $GIT_REPO_PATH
if git status; then
    git fetch
else
    git clone https://github.com/ilastik/webilastik .
fi
git checkout origin/master

PIP_BLOCK_START_LINE=$(cat $ENVIRONMENT_YML_PATH | grep -nE '^ *- *pip *:' | cut -d: -f1)

cat $ENVIRONMENT_YML_PATH | head -n $(expr $PIP_BLOCK_START_LINE - 1) > $PIPLESS_ENVIRONMENT_YML_PATH

echo "Creating the base conda environment without the pip pacakges"
# conda env create -f $PIPLESS_ENVIRONMENT_YML_PATH

# module load git
# module load Stages/2022
# module load GCC/11.2.0
# module load OpenMPI/4.1.2

# echo "Activating the newly installed environment"
# conda activate webilastik

echo "Installing the pip packages, giving them  a chance to compile with the HPC compilers"
ENVIRONMENT_YML_NUM_LINES=$(cat $ENVIRONMENT_YML_PATH | wc -l)
PIP_PACKAGE_NUM_LINES=$(expr $ENVIRONMENT_YML_NUM_LINES - $PIP_BLOCK_START_LINE)
PIP_PACKAGE_NAMES=$(cat $ENVIRONMENT_YML_PATH | tail -n $PIP_PACKAGE_NUM_LINES | sed 's@^ *- *@@' | tr '\n' ' ')
pip install $PIP_PACKAGE_NAMES
