#!/bin/bash
# Build the lambdas.
set -euo pipefail

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."
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

# Build the packages
# build/ is gitignored, so it never exists on a fresh checkout - create it up front
# rather than letting the zip step fail on a missing output directory.
mkdir -p build

for TARGET in dependencies ConnectFunction CheckFunction MetricsFunction
do
    pushd lambdas/${TARGET}

    echo "Packaging target ${TARGET}"
    # Bug: this used to be "rm -rf ${TARGET}/build", which - since we are already inside
    # lambdas/${TARGET} via pushd - resolved to a nonexistent nested path and silently did
    # nothing, leaving stale build output (e.g. platform-mismatched .pyd files) from any
    # previous build in place for pip's -t install to skip over rather than replace.
    rm -rf build
    if [[ "$TARGET" == "dependencies" ]]; then
        BUILDDIR=build/python
    else
        BUILDDIR=build
    fi
    mkdir -p $BUILDDIR
    cp -r src/* $BUILDDIR

    # Create a temporary venv for installing production dependencies
    python -m venv venv
    # venv layout differs: bin/activate on Linux/Mac, Scripts/activate on native Windows Python.
    if [ -f venv/bin/activate ]; then
        source venv/bin/activate
    else
        source venv/Scripts/activate
    fi
    # Force Lambda-compatible (Linux, Python 3.12, x86_64) wheels regardless of the
    # host machine's own OS/Python version - building on Windows or Mac would otherwise
    # pull in native-extension wheels (e.g. rpds_py, a jsonschema dependency) compiled
    # for the wrong platform, which then fail to import at runtime in Lambda.
    pip install -r requirements.txt -t $BUILDDIR \
        --platform manylinux2014_x86_64 \
        --python-version 3.12 \
        --implementation cp \
        --abi cp312 \
        --only-binary=:all:
    deactivate
    rm -rf venv

    echo "Create a suitable zip file for an AWS lambda"
    cd build
    # We are in lambdas/TARGET/build, and we want a zip file in build
    zip -r ../../../build/${TARGET}.zip .

    # All done for this target
    popd
done

echo "SUCCESS"