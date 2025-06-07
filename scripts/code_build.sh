#!/bin/bash
# Build the lambdas.
set -euo pipefail

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."
source scripts/utils.sh

# Function to setup test environment
setup_test_venv() {
    echo "Setting up test virtual environment"
    python -m venv .venv-test
    source .venv-test/bin/activate

    # Install test dependencies for all lambda functions
    for DIR in lambdas/*/
    do
        if [ -f "${DIR}requirements-dev.txt" ]; then
            pip install -r "${DIR}requirements-dev.txt"
        fi
    done
}

# Determine whether tests should be run based on the command line argument.
if [ "$#" -gt 0 ]; then
    if [ "$1" = "test" ]; then
        echo "Run tests"
        setup_test_venv
        bash scripts/code_test.sh
        deactivate
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

# Build the packages
for TARGET in dependencies ConnectFunction CheckFunction MetricsFunction
do
    pushd lambdas/${TARGET}

    echo "Packaging target ${TARGET}"
    rm -rf ${TARGET}/build
    if [[ "$TARGET" == "dependencies" ]]; then
        BUILDDIR=build/python
    else
        BUILDDIR=build
    fi
    mkdir -p $BUILDDIR
    cp -r src/* $BUILDDIR

    # Create a temporary venv for installing production dependencies
    python -m venv .venv-build
    source .venv-build/bin/activate
    pip install -r requirements.txt -t $BUILDDIR
    deactivate
    rm -rf .venv-build

    echo "Create a suitable zip file for an AWS lambda"
    cd build
    # We are in lambdas/TARGET/build, and we want a zip file in build
    zip -r ../../../build/${TARGET}.zip .

    # All done for this target
    popd
done

echo "SUCCESS"