#!/bin/bash
# Set up AWS Connect fields.
set -euo pipefail
echo "Environment: ${ENVIRONMENT}"
echo "App: ${APP}"

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."
source scripts/utils.sh

INSTANCE_ALIAS="${APP}-${ENVIRONMENT}"
FLOW_NAME="${APP} flow"

# This is really just ugly.
aws connect list-instances
INSTANCE=$(aws connect list-instances --query "InstanceSummaryList[?InstanceAlias=='${INSTANCE_ALIAS}'].Id" --output text)

if [ -z "$INSTANCE" ]; then
  echo "Error: No instance found for alias ${INSTANCE_ALIAS}" >&2
  exit 1
fi

echo "Found instance of alias ${INSTANCE_ALIAS}, ID ${INSTANCE}"

# Get the URN of the connect function.
FUNCTION_ARN=$(aws lambda get-function --function-name ConnectFunction | jq ".Configuration.FunctionArn" -r)
echo "Found instance of ConnectFunction with ARN ${FUNCTION_ARN}"

# Associate our lambda functions
echo "Associate lambda function with AWS Connect"
aws connect associate-lambda-function --instance-id ${INSTANCE} --function-arn ${FUNCTION_ARN}

# Create the actual flow.
# The lambda function URN is are hard coded in the exported JSON files; replace them.
echo "Create contact flow"
CONTENT=$(cat resources/LoneWorkerFlow.json | sed "s/\"LambdaFunctionARN\":\".*\"/\"LambdaFunctionARN\": \"${FUNCTION_ARN}\"/g")
#aws connect delete-contact-flow --instance-id ${INSTANCE} --name "${FLOW_NAME}"
aws connect create-contact-flow --instance-id ${INSTANCE} --name "${FLOW_NAME}" --type CONTACT_FLOW --content "${CONTENT}"

echo "SUCCESS"
