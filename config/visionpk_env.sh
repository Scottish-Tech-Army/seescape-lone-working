# Parameters required for each environment.
# Region to use
export AWS_REGION=eu-west-2

# Config file - outside the repo as it contains email addresses.
export CONFIG_FILE=../visionpk.yaml

# Various other parameters that must be passed around into both scripts and cloudformation.
# None of these may include spaces or special characters.
# These variables normally have to be distinct for each environment
export BUCKET_NAME=visionpk-loneworker-bucket
export ENVIRONMENT=visionpk-test      # Test suffix is wrong, but not worth changing now deployed

# Number of reserved instances for performance. A good value is normally 1 or 2,
# but you can set it to 0 if AWS quotas are preventing it working.
export CONCURRENCY=0

# These normally do not have to be distinct; leave unchanged unless you have a good reason.
export APP=loneworker # Used for tags and naming
