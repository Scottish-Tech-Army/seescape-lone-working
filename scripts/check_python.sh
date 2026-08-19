#!/bin/bash
# Abort unless the host's python3 matches the Lambda runtime pinned in
# config/global_config.sh.
#
# code_build.sh and code_test.sh both create their venvs with python3, and pip
# resolves wheels for whatever interpreter it runs under. So building on the
# wrong host Python produces artefacts tagged for a runtime the lambdas do not
# run on, and testing on the wrong host Python risks green results that do not
# reflect the deployed runtime's behaviour.
#
# The build case is the dangerous one. Compiled dependencies with no
# pure-Python fallback (notably rpds-py, pulled in by jsonschema) do not fail
# at build or deploy time - the zip builds, the stack updates, and the lambda
# then dies with an ImportError the first time it cold-starts. This check is
# the only thing that catches that before it reaches production.
set -euo pipefail

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."

source config/global_config.sh

EXPECTED_VERSION="${PYTHON_VERSION}"

PYTHON3_PATH=$(command -v python3 || true)

if [ -z "$PYTHON3_PATH" ]; then
    echo "ERROR: 'python3' not found on PATH. Install or activate Python ${EXPECTED_VERSION}." >&2
    exit 1
fi

# Invoked via the resolved path, not a bare "python3", so the interpreter
# reported in the error below is provably the one that was version-checked.
ACTUAL_VERSION=$("$PYTHON3_PATH" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

if [ "${ACTUAL_VERSION}" != "${EXPECTED_VERSION}" ]; then
    echo "ERROR: config/global_config.sh pins python${EXPECTED_VERSION}, but 'python3' (${PYTHON3_PATH}) resolves to ${ACTUAL_VERSION}." >&2
    exit 1
fi

echo "Python version check passed: python3 is ${ACTUAL_VERSION}, matching expected ${EXPECTED_VERSION}"
