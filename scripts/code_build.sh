#!/bin/bash
# Build the lambdas.
set -euo pipefail

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."

# Abort before creating any venv if the host interpreter doesn't match the
# Lambda runtime pinned in config/global_config.sh.
bash scripts/check_python.sh

source scripts/utils.sh

# Determine whether tests should be run based on the command line argument.
if [ "$#" -gt 0 ]; then
    if [ "$1" = "test" ]; then
        echo "Run tests"
        bash scripts/code_test.sh
    elif [ "$1" = "notest" ]; then
        echo "Do not run tests"
    else
        echo "Usage: $0 {test|notest}" >&2
        exit 1
    fi
else
    echo "Usage: $0 {test|notest}" >&2
    exit 1
fi

# The zip files are written here. It is git-ignored, so it does not exist on a
# fresh checkout, and zip will not create a missing destination directory.
mkdir -p build

# Build the packages
for TARGET in dependencies ConnectFunction CheckFunction MetricsFunction
do
    pushd lambdas/${TARGET}

    echo "Packaging target ${TARGET}"
    # We are already in lambdas/TARGET, so this clears lambdas/TARGET/build
    rm -rf build
    if [[ "$TARGET" == "dependencies" ]]; then
        BUILDDIR=build/python
    else
        BUILDDIR=build
    fi
    mkdir -p $BUILDDIR
    cp -r src/* $BUILDDIR
    # src/__pycache__ is written by test runs on the host, so it can hold .pyc
    # files built by a previous Python version. Dropping it keeps the stale
    # bytecode out of the package. (src/ is flat, so this is the only one that
    # can arrive this way; the caches pip generates below are built fresh.)
    rm -rf "${BUILDDIR}/__pycache__"

    # Create a temporary venv for installing production dependencies
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt -t $BUILDDIR
    deactivate
    rm -rf venv

    echo "Create a suitable zip file for an AWS lambda"
    cd build
    # We are in lambdas/TARGET/build, and we want a zip file in build.
    # Remove any stale zip first: zip adds/replaces entries but never
    # deletes ones no longer present on disk, so an existing archive
    # would keep artefacts from a previous build.
    rm -f ../../../build/${TARGET}.zip
    zip -r ../../../build/${TARGET}.zip .

    # All done for this target
    popd
done

echo "SUCCESS"