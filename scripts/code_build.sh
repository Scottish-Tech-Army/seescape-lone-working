#!/bin/bash
# Build the lambdas.
set -euo pipefail
echo "Environment: ${ENVIRONMENT}"
echo "App: ${APP}"

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."

# No tests yet
RUNTESTS=false

# Set up where all the built zip files will go.
mkdir -p build
rm build/*.zip

# Build the packages
for TARGET in dependencies ConnectFunction CheckFunction
do
    pushd lambdas/${TARGET}

    if [[ "${RUNTESTS:-}" == "true" ]]; then
        echo "Testing target ${TARGET}"
        VENV=${TARGET}/venv
        python -m venv ${VENV}
        . ${VENV}/bin/activate
        pip install -r requirements.txt
        # Run tests at this point.
        echo "No actual tests"
        deactivate
    else
        echo "Tests not run for target ${TARGET}"
    fi

    echo "Packaging target ${TARGET}"
    rm -rf ${TARGET}/build
    if [[ "$TARGET" == "dependencies" ]]; then
        BUILDDIR=build/python
    else
        BUILDDIR=build
    fi
    mkdir -p $BUILDDIR
    cp -r src/* $BUILDDIR
    pip install -r requirements.txt -t $BUILDDIR

    echo "Create a suitable zip file for an AWS lambda"
    cd build
    # We are in lambdas/TARGET/build, and we want a zip file in build
    zip -r ../../../build/${TARGET}.zip .

    # Push those zip files into the S3 bucket
    popd
done
