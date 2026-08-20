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
    # src/__pycache__ is written by test runs on the host, so it can hold .pyc
    # files built by a previous Python version. Dropping it keeps the stale
    # bytecode out of the package. (src/ is flat, so this is the only one that
    # can arrive this way; the caches pip generates below are built fresh.)
    rm -rf "${BUILDDIR}/__pycache__"

    # Create a temporary venv for installing production dependencies
    python3 -m venv venv
    # venv layout differs: bin/activate on Linux/Mac, Scripts/activate on native Windows Python.
    if [ -f venv/bin/activate ]; then
        source venv/bin/activate
    else
        source venv/Scripts/activate
    fi
    # check_python.sh has already confirmed the host's python3 matches the pinned
    # Lambda runtime version, so --python-version/--abi don't need to be forced here.
    # --platform/--only-binary still need forcing though: building on Windows or Mac
    # would otherwise pull in native-extension wheels (e.g. rpds_py, a jsonschema
    # dependency) compiled for the host's own OS/architecture, which then fail to
    # import at runtime in Lambda (which always runs manylinux x86_64).
    pip install -r requirements.txt -t $BUILDDIR \
        --platform manylinux2014_x86_64 \
        --only-binary=:all:
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