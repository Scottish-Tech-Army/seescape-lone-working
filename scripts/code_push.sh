#!/bin/bash
# Push lambdas that have been built into S3.
set -euo pipefail
echo "Environment: ${ENVIRONMENT}"
echo "App: ${APP}"

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."

# Name of our dependency layer
LAYER_NAME=${APP}-lambda-dependencies

# You might think "surely this could be laid out more rationally". Yes, it could, but
# commands on the same function need to be separated by a second or two for reasons,
# and so we jump back and forth between doing things on each function and doing things
# on the dependency layer so that things do not fail.
for TARGET in dependencies ConnectFunction CheckFunction
do
    echo "Uploading ${TARGET} to S3"
    aws s3 cp build/${TARGET}.zip s3://${BUCKET_NAME}/lambdas/${TARGET}
done

if ! aws lambda get-function --function-name ConnectFunction > /dev/null 2>&1
then
    echo "ConnectFunction does not exist - dropping out"
    exit 0
fi

# Get list of dependency layers ready for deletion later. We do this before we later create a new layer.
LAYER_NUMBERS=$(aws lambda list-layer-versions --layer-name ${LAYER_NAME} | jq -r '.LayerVersions | map(.Version) | sort | join(" ")')
echo "Current list of layer numbers: ${LAYER_NUMBERS}"

for TARGET in ConnectFunction CheckFunction
do
    echo "Forcing ${TARGET} code to the new version  "
    aws lambda update-function-code \
        --function-name ${TARGET} \
        --s3-bucket ${BUCKET_NAME} \
        --s3-key lambdas/${TARGET}
done

echo "Update dependency layer version"
VERSION=$(aws lambda publish-layer-version --layer-name ${LAYER_NAME} --content S3Bucket=${BUCKET_NAME},S3Key=lambdas/dependencies | jq ".LayerVersionArn" -r)

for TARGET in ConnectFunction CheckFunction
do
    echo "Updating dependencies for ${TARGET} to ${VERSION}"
    aws lambda update-function-configuration --function-name ${TARGET} --layers ${VERSION}
done

# This generates a new layer every time it runs. Tidy up old layers; we do not care about them.
echo "Tidy up layers ${LAYER_NUMBERS}"
for NUMBER in ${LAYER_NUMBERS}
do
    echo "Delete layer ${NUMBER}"
    aws lambda delete-layer-version --layer-name ${LAYER_NAME} --version-number ${NUMBER}
done

echo "TODO: REINSTATE THIS, BROKEN BY QUOTA LIMITATIONS"
exit 0

# Now set up concurrency for the ConnectFunction. We do not care about CheckFunction (that is async)
echo "Update concurrency for ConnectFunction (only)"
FUNCTION_VERSIONS=$(aws lambda list-versions-by-function --function-name ConnectFunction | jq -r '.Versions | map(.Version) | sort | join(" ")')
echo "  existing versions ${FUNCTION_VERSIONS}"
for VERSION in $(echo ${FUNCTION_VERSIONS} | awk '{for(i=2;i<NF;i++) printf $i " ";}')
do
    echo "  remove version ${VERSION}"
    aws lambda delete-function --function-name ConnectFunction --qualifier ${VERSION}
done

VERSION=$(aws lambda publish-version --function-name ConnectFunction | jq ".Version" -r)
echo "  published version ${VERSION}"
aws lambda put-provisioned-concurrency-config --function-name ConnectFunction \
  --qualifier ${VERSION} \
  --provisioned-concurrent-executions 1