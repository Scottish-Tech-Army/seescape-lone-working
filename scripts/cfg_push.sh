#!/bin/bash
# Validate and push configuration into S3.
set -euo pipefail
echo "Environment: ${ENVIRONMENT}"
echo "App: ${APP}"

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."
source scripts/utils.sh

CFG_FULL_PATH="config/${CONFIG_FILE}"

echo "Loading configuration file ${CFG_FULL_PATH}"
echo "  Validating file"
python lambdas/dependencies/src/cfg_parser.py ${CFG_FULL_PATH}

# Validated - upload.
echo "  Uploading to parameter store"
VALUE=$(cat ${CFG_FULL_PATH})

PARAMETER_PATH="/${APP}/config"
if aws ssm get-parameter --name ${PARAMETER_PATH} --query 'Parameter.Name' --output text >/dev/null 2>&1; then
    echo "  Updating in parameter store"
    aws ssm put-parameter --name ${PARAMETER_PATH} --description "General configuration file" \
                        --value "$VALUE" --type "String" \
                        --overwrite
else
    echo "  Adding to parameter store"
    aws ssm put-parameter --name ${PARAMETER_PATH} --description "General configuration file" \
                        --value "$VALUE" --type "String" \
                        --tags ${TAGS}
fi

echo "SUCCESS"