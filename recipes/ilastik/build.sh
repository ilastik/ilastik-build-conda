cp -r ./ ${PREFIX}/ilastik
cd ${PREFIX}/ilastik
git checkout ${GIT_FULL_HASH}
git submodule init
git submodule update --recursive

# set version according to tag!
python ${RECIPE_DIR}/set_version.py ${PREFIX}/ilastik/ilastik/__init__.py ${PKG_VERSION}

# Remove the git repo files.
rm -rf .git

# Create .pyc files
python -m compileall ilastik

# Add the ilastik modules to sys.path
cat > ${SP_DIR}/ilastik.pth << EOF
../../../ilastik/volumina
../../../ilastik
EOF
