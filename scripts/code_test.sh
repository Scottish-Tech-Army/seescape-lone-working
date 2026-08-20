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
# "python3 -m venv" on an existing directory does not clear old site-packages,
# so a venv created under a previously-pinned Python version can leave native
# extensions (e.g. rpds_py) compiled for that old version in place. They then
# fail to import under the new interpreter even though pyvenv.cfg correctly
# reports the new version. Always start clean.
rm -rf venv
python3 -m venv venv
# venv layout differs: bin/activate on Linux/Mac, Scripts/activate on native Windows Python.
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
else
    source venv/Scripts/activate
fi

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