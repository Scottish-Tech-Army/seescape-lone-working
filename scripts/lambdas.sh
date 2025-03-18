#!/bin/bash
# Set up initial deployment. This should not be rerun.
set -euo pipefail
echo "Environment: ${ENVIRONMENT}"
echo "App: ${APP}"

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."
source scripts/utils.sh

STACK_NAME="${APP}-lambdas"
create_or_update_stack ${STACK_NAME} "lambdas.yaml"  "--capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM"

STACK_NAME="${APP}-dashboard"
create_or_update_stack ${STACK_NAME} "dashboard.yaml"



echo "SUCCESS"
