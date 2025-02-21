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

# Go to build the dependencies
for TARGET in dependencies connectfunction checkfunction
do
    pushd lambdas/${TARGET}

    if [[ "${RUNTESTS:-}" == "true" ]]; then
        echo "Testing target ${TARGET}"
        python -m venv ${TARGET}/.venv
        . .venv/bin/activate
        pip install -r requirements.txt
        # Run tests at this point.
        echo "No actual tests"
        deactivate
    else
        echo "Tests not run for target ${TARGET}"
    fi

    echo "Packaging target ${TARGET}"
    if [[ "$TARGET" == "dependencies" ]]; then
        BUILDDIR=build/python
    else
        BUILDDIR=build
    fi
    rm -rf $BUILDDIR
    mkdir $BUILDDIR
    cp -r src/* $BUILDDIR
    pip install -r requirements.txt -t $BUILDDIR

    echo "Create a suitable zip file for an AWS lambda"
    cd build
    # We are in lambdas/TARGET/build, and we want a zip file in build
    zip -r ../../../build/${TARGET}.zip .

    # Push those zip files into the S3 bucket
    popd
done

echo "Uploading to S3"

for TARGET in dependencies connectfunction checkfunction
do
    echo "Uploading ${TARGET}"
    aws s3 cp build/${TARGET}.zip s3://${BUCKET_NAME}/lambdas/${TARGET}
done

# This has a different capitalisation
for TARGET in ConnectFunction CheckFunction
do
    if ! aws lambda get-function --function-name ${TARGET} > /dev/null 2>&1
    then
        echo "Function ${TARGET} does not exist; ignoring"
    else
        echo "Forcing ${TARGET} to the new version"
        aws lambda update-function-code \
            --function-name ${TARGET} \
            --s3-bucket ${BUCKET_NAME} \
            --s3-key lambdas/${TARGET}
    fi
done
