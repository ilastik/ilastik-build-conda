#!/bin/bash

##
## Usage: create-tarball.sh[--include-tests] release-name
##

set -e

INCLUDE_TESTS=0
if [[ $@ == *"--include-tests"* ]]; then
    if [[ $1 == "--include-tests" ]]; then
        INCLUDE_TESTS=1
        shift
    else
        echo "Error: --include-tests may only be provided as the first arg (or after --no-solvers)." >&2
        exit 1
    fi
fi


RELEASE_NAME=$1

CONDA_ROOT=`conda info --root`
source ${CONDA_ROOT}/bin/activate root

RELEASE_ENV=${CONDA_ROOT}/envs/ilastik-release


echo "Creating release ${RELEASE_NAME} from ${RELEASE_ENV}"

# Remove cplex libs/symlinks (if present)
rm -f ${CONDA_ROOT}/envs/ilastik-release/lib/libcplex.so
rm -f ${CONDA_ROOT}/envs/ilastik-release/lib/libilocplex.so
rm -f ${CONDA_ROOT}/envs/ilastik-release/lib/libconcert.so

# Remove gurobi symlinks (if present)
rm -f ${RELEASE_ENV}/lib/libgurobi*.so

if [[ $INCLUDE_TESTS == 1 ]]; then
    echo "Including ilastik tests in release (larger release size)."
else
    echo "Removing ilastik tests from source folders"
    ILASTIK_META=${CONDA_ROOT}/envs/ilastik-release/ilastik-meta
    rm -rf ${ILASTIK_META}/*/tests/*
    echo "test-files removed"
fi

if [[ $SKIP_TAR == 1 ]]; then
    echo "Skipping tarball creation."
    echo "Release env created in ${CONDA_ROOT}/envs/ilastik-release"
else
    # Create the tarball, and move it to the current directory.
    echo "Creating ${RELEASE_NAME}.tar.bz2"
    DEST_DIR=`pwd`
    cd ${CONDA_ROOT}/envs/
    mv ilastik-release ${RELEASE_NAME}
    tar -cjf $DEST_DIR/${RELEASE_NAME}.tar.bz2 ${RELEASE_NAME}
    mv ${RELEASE_NAME} ilastik-release
    cd -
fi
