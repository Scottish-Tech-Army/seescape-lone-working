#!/bin/bash
# Set up AWS Connect fields.
set -euo pipefail
echo "Environment: ${ENVIRONMENT}"
echo "App: ${APP}"

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."

INSTANCE_ALIAS="${APP}-${ENVIRONMENT}"
FLOW_NAME="${APP} flow"

# This is really just ugly.
aws connect list-instances 
INSTANCE=$(aws connect list-instances --query "InstanceSummaryList[?InstanceAlias=='${INSTANCE_ALIAS}'].Id" --output text)
echo "Found instance of alias ${INSTANCE_ALIAS}, ID ${INSTANCE}"

# Get the URN of the connect function.
FUNCTION_ARN=$(aws lambda get-function --function-name ConnectFunction | jq ".Configuration.FunctionArn" -r)
echo "Found instance of ConnectFunction with ARN ${FUNCTION_ARN}"

# Associate our lambda functions
echo "Associate lambda function with AWS Connect"
aws connect associate-lambda-function --instance-id ${INSTANCE} --function-arn ${FUNCTION_ARN}

# Create the actual flow.
# The lambda function names and URNs are hard coded in the exported JSON files; replace them.
echo "Create contact flow"
CONTENT=$(cat resources/LoneWorkerFlow.json | sed s/LAMBDA_ARN/${FUNCTION_ARN}/g)
#aws connect delete-contact-flow --instance-id ${INSTANCE} --name "${FLOW_NAME}"
aws connect create-contact-flow --instance-id ${INSTANCE} --name "${FLOW_NAME}" --type CONTACT_FLOW --content "${CONTENT}"

exit 0

# Still to be added.

# Set up a phone number
# Yes, there are prerequisites to actually get a number
aws connect list-phone-numbers-v2 --instance-id ${INSTANCE}
aws connect claim-phone-number --phone-number ${NUMBER}
aws connect associate-phone-number-contact-flow

# Optional prompts
aws connect list-prompts --instance-id ${INSTANCE}
aws connect create-prompt --instance-id ${INSTANCE} --name "hello" --s3-uri (whatever) --tags ${TAGS}

