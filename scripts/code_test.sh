#!/bin/bash
# Test the lambdas.
set -euo pipefail

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."

# Ensure we're in the test venv
if [[ -z "${VIRTUAL_ENV:-}" ]] || [[ ! "${VIRTUAL_ENV}" == *".venv-test" ]]; then
    echo "Error: Must be run from within the test virtual environment"
    exit 1
fi

pushd lambdas

echo "Run tests"
pytest -o log_cli=true -o log_cli_level=info

popd

echo "SUCCESS"