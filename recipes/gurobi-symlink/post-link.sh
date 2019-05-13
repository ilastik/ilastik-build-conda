set -e
GUROBI_LOCATION_CACHE_FILE="$(conda info --root)/share/gurobi-root-dir.path"

# SHLIB_EXT is not available at install time
if [ $(uname) == "Darwin" ]; then
        SHLIB_EXT="dylib"
else
        SHLIB_EXT="so"
fi


if [ "$GUROBI_ROOT_DIR" == "" ]; then 
    GUROBI_ROOT_DIR="<UNDEFINED>"
fi

if [ "$GUROBI_ROOT_DIR" != "<UNDEFINED>" ]; then
    # If the environment-provided GUROBI_ROOT_DIR doesn't match the 
    #  cache-provided value, (over)write the cache file.
    SAVED_GUROBI_ROOT_DIR=$(cat ${GUROBI_LOCATION_CACHE_FILE} 2> /dev/null) \
    || SAVED_GUROBI_ROOT_DIR="<UNDEFINED>"
    if [ "$SAVED_GUROBI_ROOT_DIR" != "$GUROBI_ROOT_DIR" ]; then
	echo "${GUROBI_ROOT_DIR}" > ${GUROBI_LOCATION_CACHE_FILE}
    fi
fi 

if [ "$GUROBI_ROOT_DIR" == "<UNDEFINED>" ]; then
    # If we've installed at least once on this machine, 
    # then we can get GUROBI_ROOT_DIR from our the cache file.
    GUROBI_ROOT_DIR=$(cat ${GUROBI_LOCATION_CACHE_FILE} 2> /dev/null) \
    || GUROBI_ROOT_DIR="<UNDEFINED>"
fi

if [ "$GUROBI_ROOT_DIR" == "<UNDEFINED>" ]; then
    set +x
    echo "******************************************************"
    echo "* You must define GUROBI_ROOT_DIR in your environment *"
    echo "* before using gurobi-symlink for the first time.      *"
    echo "******************************************************"
    exit 1
fi

GUROBI_LIB_DIR=$(echo $GUROBI_ROOT_DIR/lib)

set -x

# Symlink the gurobi libraries into the lib directory
(
    mkdir -p ${PREFIX}/lib
    cd ${PREFIX}/lib
    
    if [ -z "$(ls ${GUROBI_LIB_DIR}/*.${SHLIB_EXT})" ]; then
        1>&2 echo "******************************************************"
        1>&2 echo "Error: No shared libraries found in ${GUROBI_LIB_DIR}"
        1>&2 echo "******************************************************"
        exit 1
    fi
    
    for f in $(ls ${GUROBI_LIB_DIR}/*.${SHLIB_EXT}); do
        ln -f -s ${f}
    done
)
