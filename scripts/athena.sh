#!/bin/bash
# Set up initial deployment. This should not be rerun.
set -euo pipefail
echo "Environment: ${ENVIRONMENT}"
echo "App: ${APP}"

# This script must run from the parent directory of the scripts directory
cd "$(dirname "$0")/.."
source scripts/utils.sh

WORKGROUP_NAME="${APP}-athena"
DATABASE="${APP}"
TABLE="${DATABASE}.metrics"

# We ought to use cloudformation, but cloudformation for athena is a horrible mess - it isn't idempotent.

# Check if the workgroup already exists
EXISTING_WORKGROUP=$(aws athena list-work-groups --query "WorkGroups[?Name=='$WORKGROUP_NAME'].Name" --output text)

if [ "$EXISTING_WORKGROUP" == "$WORKGROUP_NAME" ]; then
  echo "Workgroup '$WORKGROUP_NAME' already exists."
else
  echo "Creating workgroup '$WORKGROUP_NAME'..."
  aws athena create-work-group \
    --name "$WORKGROUP_NAME" \
    --description "Description of your workgroup" \
    --configuration "{\"ResultConfiguration\": {\"OutputLocation\": \"s3://${BUCKET_NAME}/athena-results/\"}}"

  echo "Workgroup '$WORKGROUP_NAME' created successfully."
fi

aws athena start-query-execution \
    --query-string "CREATE DATABASE IF NOT EXISTS ${DATABASE};" \
    --work-group ${WORKGROUP_NAME}

aws athena start-query-execution \
    --query-string "CREATE EXTERNAL TABLE IF NOT EXISTS ${TABLE} (
          Namespace    STRING,
          MetricName   STRING,
          Dimensions   STRING,
          Timestamp    TIMESTAMP,
          Average      DOUBLE,
          Minimum      DOUBLE,
          Maximum      DOUBLE,
          Sum          DOUBLE,
          SampleCount  DOUBLE
      )
      PARTITIONED BY (year STRING, month STRING)

      ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
      WITH SERDEPROPERTIES (
          'separatorChar' = ',',
          'quoteChar' = '\"'
      )
      STORED AS TEXTFILE
      LOCATION 's3://${BUCKET_NAME}/metrics/';" \
    --work-group ${WORKGROUP_NAME}

aws athena start-query-execution \
    --query-string "MSCK REPAIR TABLE ${TABLE};" \
    --work-group ${WORKGROUP_NAME}

echo "SUCCESS"
