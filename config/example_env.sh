# Example configuration file, to be created for each environment.
# Name of AWS profile to use.
export AWS_PROFILE=my-profile

# This must be a valid yaml file in the same directory.
export CONFIG_FILE=example.yaml

# Various other parameters that must be passed around into both scripts and cloudformation.
# None of these may include spaces or special characters.
# These variables normally have to be distinct for each environment
export BUCKET_NAME=some-bucket-name # S3 bucket to be created and used for lambda storage
export ENVIRONMENT=some-env-tag     # Environment name, used in some tags

# Number of reserved lambda instances for performance. A good value is normally 1.
# - Set it to 0 if AWS quotas are preventing it working or you are cost sensitive.
# - Set it to 2 if you are using the system very heavily, and concurrent calls often happen.
# Note that there are costs proportional to the value.
export CONCURRENCY=0

# From here on, you should probably just use the default unless you have a good reason.
# Name of the app, used in naming pretty much all resources.
export APP=loneworker # Used for tags and naming
