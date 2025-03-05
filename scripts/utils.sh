#!/bin/bash
# Utility functions for various deployment code
set -euo pipefail

# Parameters for cloud formation
export PARAMETERS="ParameterKey=bucketName,ParameterValue=${BUCKET_NAME} ParameterKey=environment,ParameterValue=${ENVIRONMENT} ParameterKey=app,ParameterValue=${APP}"
# Tags to be supplied on resources
export TAGS="Key=app,Value=${APP} Key=env,Value=${ENVIRONMENT}"

create_or_update_stack() {
    # Arguments:
    # - Stack name
    # - YAML file (in the templates directory)
    # - extra args (such as capabilities) - optional
    # Sets the value to be performed - either "create-stack" or "update-stack" - in the variable OPERATION
    local STACK_NAME=$1
    local YAML_FILE=$2
    local EXTRA_ARGS=${3:-""}
    echo "Creating or updating stack ${STACK_NAME}"
    if ! aws cloudformation describe-stacks --stack-name ${STACK_NAME} > /dev/null 2>&1
    then
        echo "  Stack does not exist. Creating stack."
        OPERATION=create-stack
    else
        echo "  Stack exists. Updating stack."
        OPERATION=update-stack
    fi

    aws cloudformation ${OPERATION} --stack-name ${STACK_NAME} \
                                    --template-body file://templates/${YAML_FILE} \
                                    ${EXTRA_ARGS} \
                                    --parameters ${PARAMETERS} \
                                    --tags ${TAGS}

    aws cloudformation describe-stacks --stack-name ${STACK_NAME}
}
