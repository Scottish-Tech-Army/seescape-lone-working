# Parameters required for each environment.
# Convenience variables used only by the aws CLI. Not mandatory.
export AWS_PROFILE=seescape

# This must be a valid yaml file in the same directory.
export CONFIG_FILE=seescape.yaml

# Various other parameters that must be passed around into both scripts and cloudformation.
# None of these may include spaces or special characters.
# These variables normally have to be distinct for each environment
export BUCKET_NAME=aws-sam-cli-managed-default-samclisourcebucket-3rhhfpjblgdf
export ENVIRONMENT=seescape             # Environment name, used in some tags

# Number of reserved instances for performance. A good value is normally 1 or 2,
# but you can set it to 0 if AWS quotas are preventing it working.
export CONCURRENCY=1

# These normally do not have to be distinct; leave unchanged unless you have a good reason.
export APP=loneworker # Used for tags and naming
