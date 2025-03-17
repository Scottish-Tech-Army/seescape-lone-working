#!/bin/bash
# Set up initial deployment. This should not be rerun.
set -euo pipefail
echo "Environment: ${ENVIRONMENT}"
echo "App: ${APP}"

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."
source scripts/utils.sh

STACK_NAME="${APP}-initial"

# Create the stack
create_or_update_stack ${STACK_NAME} "initial.yaml"

# Check if the secrets already exist, and drop out if they do, so we can rerun this script.
if aws ssm get-parameter --name /${APP}/tenant --query 'Parameter.Name' --output text >/dev/null 2>&1; then
    echo "Secret parameters already exist - dropping out."
    exit 0
fi

# Create the secrets; this is how it should be done so they are stored encrypted.
# Note that this just puts in dummy values. There is a later step to manually set these dummy values correctly.
echo "Creating secrets"
if [ "${OAUTH2_FLOW}" == "ropc" ]; then
    echo "  email password"
    aws ssm put-parameter --name /${APP}/emailpass --description "Password for email account" \
                        --value "DummySecretValue" --type "SecureString" \
                        --tags ${TAGS}
elif [ "${OAUTH2_FLOW}" == "client" ]; then
    echo "  client secret"
    aws ssm put-parameter --name /${APP}/clientsecret --description "Client secret for M365 application" \
                        --value "DummySecretValue" --type "SecureString" \
                        --tags ${TAGS}
else
    echo "Error: OAUTH2_FLOW must be either 'ropc' or 'client'"
    exit 1
fi

echo "  tenant ID"
aws ssm put-parameter --name /${APP}/tenant --description "Tenant ID for M365 application" \
                      --value "DummySecretValue" --type "SecureString" \
                      --tags ${TAGS}

echo "  client ID"
aws ssm put-parameter --name /${APP}/clientid --description "Client ID for M365 application" \
                      --value "DummySecretValue" --type "SecureString" \
                      --tags ${TAGS}

echo "  email address"
aws ssm put-parameter --name /${APP}/emailuser --description "Email user (in form of email address)" \
                      --value "DummySecretValue" --type "SecureString" \
                      --tags ${TAGS}

echo "SUCCESS"