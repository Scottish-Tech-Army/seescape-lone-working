#!/bin/bash
# Validate and push configuration into S3.
set -euo pipefail
echo "Environment: ${ENVIRONMENT}"
echo "App: ${APP}"

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."
source scripts/utils.sh

if [[ "${CONFIG_FILE}" == */* ]]; then
    CFG_FULL_PATH="${CONFIG_FILE}"
else
    CFG_FULL_PATH="config/${CONFIG_FILE}"
fi

echo "Loading configuration file ${CFG_FULL_PATH}"
echo "  Validating file"

# Validation runs cfg_parser.py, which imports jsonschema. We use a top-level
# venv so the dependency does not have to be installed on the host Python.
# The venv is named "venv" so .gitignore and code_clean.sh pick it up.
# Unlike code_build.sh and code_test.sh, this script does not run
# check_python.sh: this venv only runs cfg_parser.py locally and never
# produces a lambda deployment artefact, so the runtime pin in
# config/global_config.sh does not apply to it.
#
# It still needs to match whatever the host's current python3 is, though - a
# venv left over from before a host Python upgrade (e.g. this repo's own
# migration to 3.14) keeps native extensions (e.g. rpds_py) compiled for the
# old version, which then fail to import under the new interpreter even
# though the venv still looks intact. So always start clean rather than
# reusing an existing directory.
rm -rf venv
echo "  Creating venv for scripts"
python3 -m venv venv
# venv layout differs: bin/ on Linux/Mac, Scripts/ on native Windows Python.
if [ -d venv/bin ]; then
    VENV_BIN=venv/bin
else
    VENV_BIN=venv/Scripts
fi
${VENV_BIN}/pip install --quiet -r scripts/requirements.txt
${VENV_BIN}/python lambdas/dependencies/src/cfg_parser.py ${CFG_FULL_PATH}

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