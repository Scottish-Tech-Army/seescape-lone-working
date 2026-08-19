#!/bin/bash
# Test the lambdas.
set -euo pipefail

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."

# Abort before creating any venv if the host interpreter doesn't match the
# Lambda runtime pinned in config/global_config.sh.
bash scripts/check_python.sh

# Set up the test venv, under the lambda directory.
echo "Setting up test virtual environment and installing dependencies"
pushd lambdas
python3 -m venv venv
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