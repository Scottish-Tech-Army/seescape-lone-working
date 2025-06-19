#!/bin/bash
# Test the lambdas.
set -euo pipefail

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."

# Set up the test venv, under the lambda directory.
echo "Setting up test virtual environment and installing dependencies"
pushd lambdas
python -m venv venv
source venv/bin/activate

# Install test dependencies for all lambda functions
for DIR in */
do
    if [ -f "${DIR}requirements-dev.txt" ]; then
        pip install -r "${DIR}requirements-dev.txt"
    fi
done

echo "Run tests"
pytest -o log_cli=true -o log_cli_level=info

# Deactivate the test virtual environment
deactivate

popd

echo "SUCCESS"