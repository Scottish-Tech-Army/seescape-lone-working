#!/bin/bash
# Test the lambdas.
set -euo pipefail

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."
pushd lambdas

echo "Run tests"
pytest -o log_cli=true -o log_cli_level=info

popd

echo "SUCCESS"