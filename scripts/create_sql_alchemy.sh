#!/usr/bin/bash
# Create a SQL Alchemy connection string for Athena
set -euo pipefail

REGION=$(aws configure get region)
echo "Using region: $REGION"

ACCESS_JSON=$(aws iam create-access-key --user-name AthenaReadOnlyUser)
ACCESS_KEY_ID=$(echo ${ACCESS_JSON} | jq '.AccessKey.AccessKeyId' -er)
echo "Access Key ID found OK"
SECRET_ACCESS_KEY=$(echo ${ACCESS_JSON} | jq '.AccessKey.SecretAccessKey' -er)
echo "Secret access Key ID found OK"
echo

ENCODED_KEY=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "${SECRET_ACCESS_KEY}")
echo "Encoded key follows on next line:"
echo "awsathena+rest://${ACCESS_KEY_ID}:${ENCODED_KEY}@athena.${REGION}.amazonaws.com/${APP}?s3_staging_dir=s3://${BUCKET_NAME}/metrics/&work_group=${APP}-athena"
