# Global configuration, shared across all environments (unlike the
# per-environment config/*_env.sh files). Sourced by scripts/utils.sh.

# Python version the lambdas and their dependency layer target. Update this
# to move to a new Python version; it is used both to check the host's
# python3 (scripts/check_python.sh) and to fill in templates/lambdas.yaml's
# pythonVersion CloudFormation parameter.
export PYTHON_VERSION=3.14
