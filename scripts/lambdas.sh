#!/bin/bash
# Set up initial deployment. This should not be rerun.
set -euo pipefail
echo "Environment: ${ENVIRONMENT}"
echo "App: ${APP}"

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."

STACK_NAME="loneworker-lambdas"

if ! aws cloudformation describe-stacks --stack-name ${STACK_NAME} > /dev/null 2>&1
then
    echo "Stack does not exist. Creating stack."
    OPERATION=create-stack
else
    echo "Stack exists. Updating stack."
    OPERATION=update-stack
fi

aws cloudformation ${OPERATION} --stack-name ${STACK_NAME} \
                                --template-body file://templates/lambdas.yaml \
                                --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM \
                                --parameters ${PARAMETERS} \
                                --tags ${TAGS}

aws cloudformation describe-stacks --stack-name ${STACK_NAME}

