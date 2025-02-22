#!/bin/bash
# Push lambdas that have been built into S3.
set -euo pipefail
echo "Environment: ${ENVIRONMENT}"
echo "App: ${APP}"

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."

for TARGET in dependencies ConnectFunction CheckFunction
do
    echo "Uploading ${TARGET} to S3"
    aws s3 cp build/${TARGET}.zip s3://${BUCKET_NAME}/lambdas/${TARGET}
done

# Note the different capitalisation of the functions as opposed to the code directories.
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

