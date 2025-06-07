#!/bin/bash
# Clean out all the code cruft
set -euo pipefail

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."
echo "Cleaning out all python cache and build artefacts"

find . -type d -name ".pytest_cache" -exec rm -rf {} +
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type d -name ".venv-build" -exec rm -rf {} +
find . -type d -name ".venv-test" -exec rm -rf {} +

# Build the packages
for TARGET in dependencies ConnectFunction CheckFunction MetricsFunction
do
    echo "  Removing build directories and any temporary venvs for ${TARGET}"
    pushd lambdas/${TARGET} > /dev/null

    # Remove any temporary build directories
    rm -rf build/*

    popd > /dev/null
done

echo "  Removing built zip files"
rm -f build/*

echo "Done"
