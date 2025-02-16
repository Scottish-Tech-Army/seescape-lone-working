#!/bin/bash
# Set up initial deployment. This should not be rerun.
set -euo pipefail
echo "Environment: ${ENVIRONMENT}"
echo "App: ${APP}"

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."

# xxx known issue - this has the app value hardcoded in rg.json
# Also, RGs do not seem to work properly in AWS.
#aws resource-groups create-group --name "${APP}-${ENVIRONMENT}" \
#                                --description "Resource group for app ${APP}" \
#                                --resource-query file://scripts/rg.json \
#                                --tags app=${APP},env=${ENVIRONMENT}

# Create the secrets; this is how it should be done so they are stored encrypted.
# Note that this just puts in dummy values. There is a later step to manually set these dummy values correctly.
echo "Creating secrets"
aws ssm put-parameter --name /${SSMPREFIX}/clientid --description "Client ID for M365 calendar" \
                      --value "DummySecretValue" --type "SecureString" \
                      --tags ${TAGS}

aws ssm put-parameter --name /${SSMPREFIX}/clientsecret --description "Client secret for M365 calendar" \
                      --value "DummySecretValue" --type "SecureString" \
                      --tags ${TAGS}

aws ssm put-parameter --name /${SSMPREFIX}/emailpass --description "Password for email account" \
                      --value "DummySecretValue" --type "SecureString" \
                      --tags ${TAGS}

aws ssm put-parameter --name /${SSMPREFIX}/emailuser --description "Email user (in form of email address)" \
                      --value "DummySecretValue" --type "SecureString" \
                      --tags ${TAGS}

# Create the stack
echo "Creating cloud formation stack"
aws cloudformation create-stack --stack-name loneworker-initial \
                                --template-body file://templates/initial.yaml \
                                --parameters ${PARAMETERS} \
                                --tags ${TAGS}
                                #--parameters file://config/parameters.json \


aws cloudformation describe-stacks --stack-name loneworker-initial

echo "You must now update the values of the security parameters, which have placeholder values only"