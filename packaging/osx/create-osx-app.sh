#!/bin/bash

##
## Usage: create-osx-app.sh [--include-tests] release-name
##

set -e
set -x

OSX_PACKAGES_DIR=$(cd `dirname $0` && pwd)
CONDA_ROOT=`conda info --root`
source ${CONDA_ROOT}/bin/activate root

RELEASE_ENV=${CONDA_ROOT}/envs/ilastik-release

INCLUDE_TESTS=0
if [[ $@ == *"--include-tests"* ]]; then
    if [[ $1 == "--include-tests" ]]; then
        INCLUDE_TESTS=1
        shift
    else
        echo "Error: --include-tests may only be provided as the first arg." >&2
        exit 1
    fi
fi

RELEASE_NAME=$1

echo "Creating release ${RELEASE_NAME} from ${RELEASE_ENV}"
echo "Creating ilastik.app."
# For some reason, the app created by py2app has stability issues.
# (It might be related to the load order of multiple libgcc_s dylibs and/or libSystem.B.dylib.)
# As a workaround, we use py2app in "alias mode" and then manually copy the files we need into the app.
${RELEASE_ENV}/bin/python ${OSX_PACKAGES_DIR}/setup-alias-app.py py2app --alias --dist-dir .

echo "Writing qt.conf"
cat <<EOF > ilastik.app/Contents/Resources/qt.conf
; Qt Configuration file
[Paths]
Plugins = ilastik-release/plugins
EOF

# Remove cplex libs/symlinks (if present)
rm -f ${RELEASE_ENV}/lib/libcplex.dylib
rm -f ${RELEASE_ENV}/lib/libilocplex.dylib
rm -f ${RELEASE_ENV}/lib/libconcert.dylib

# Remove gurobi symlinks (if present)
rm -vf ${RELEASE_ENV}/lib/libgurobi*.{so,dylib}  # older gurobi-versions had *.so even on OSX

if [[ $INCLUDE_TESTS == 1 ]]; then
    echo "Including ilastik tests in release (larger release size)."
else
    echo "Removing ilastik tests from source folders"
    ILASTIK_META=${CONDA_ROOT}/envs/ilastik-release/ilastik-meta
    rm -rf ${ILASTIK_META}/*/tests/*
    echo "test-files removed"
fi

echo "Moving ilastik-release environment into ilastik.app bundle..."
mv ${RELEASE_ENV} ilastik.app/Contents/ilastik-release
cd ilastik.app/Contents/Resources && ln -s ../ilastik-release/ilastik-meta/ilastik/ilastik.py
cd -

echo "Updating bundle internal paths..."
# Fix __boot__ script
sed -i '' 's|^_path_inject|#_path_inject|g' ilastik.app/Contents/Resources/__boot__.py
sed -i '' "s|${CONDA_ROOT}/envs/ilastik-release/ilastik-meta/ilastik/||" ilastik.app/Contents/Resources/__boot__.py

# Fix Info.plist
sed -i '' "s|${CONDA_ROOT}/envs/ilastik-release|@executable_path/../ilastik-release|" ilastik.app/Contents/Info.plist
sed -i '' "s|\.dylib|m\.dylib|" ilastik.app/Contents/Info.plist

# Fix python executable link
rm ilastik.app/Contents/MacOS/python
cd ilastik.app/Contents/MacOS && ln -s ../ilastik-release/bin/python
cd -

# Fix app icon link
rm ilastik.app/Contents/Resources/appIcon.icns
cd ilastik.app/Contents/Resources && ln -s ../ilastik-release/ilastik-meta/ilastik/appIcon.icns
cd -

# Replace Resources/lib with a symlink
rm -rf ilastik.app/Contents/Resources/lib
cd ilastik.app/Contents/Resources && ln -s ../ilastik-release/lib
cd -

# Add a symlink to ilastik-meta so that lib/python2.7/site-packages/ilastik-meta.pth works correctly
cd ilastik.app/Contents/Resources && ln -s ../ilastik-release/ilastik-meta
cd -

echo "Renaming ilastik.app -> ${RELEASE_NAME}.app"
rm -rf ${RELEASE_NAME}.app
rm -f ${RELEASE_NAME}.tar.bz2
mv ilastik.app ${RELEASE_NAME}.app

echo "Compressing: ${RELEASE_NAME}.app -> ${RELEASE_NAME}.tar.bz2"
tar -cjf ${RELEASE_NAME}.tar.bz2 ${RELEASE_NAME}.app

