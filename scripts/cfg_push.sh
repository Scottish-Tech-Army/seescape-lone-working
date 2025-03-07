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

# Validated - copy to the latest lambda.
echo "  Uploading file"
aws s3 cp ${CFG_FULL_PATH} s3://${BUCKET_NAME}/config
