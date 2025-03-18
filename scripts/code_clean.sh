#!/bin/bash
# Clean out all the code cruft
set -euo pipefail

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."
echo "Cleaning out all python cache and build artefacts"

find . -type d -name ".pytest_cache" -exec rm -rf {} +
find . -type d -name "__pycache__" -exec rm -rf {} +

# Build the packages
for TARGET in dependencies ConnectFunction CheckFunction
do
    echo "  Removing venv and build directories for ${TARGET}"
    pushd lambdas/${TARGET} > /dev/null

    rm -rf venv
    rm -rf build/*

    popd > /dev/null
done

echo "  Removing built zip files"
rm -f build/*

echo "Done"
