import boto3
import csv
import datetime as dt
from datetime import datetime, timedelta
import io
import logging
import os
import time

logger = logging.getLogger(__name__)
# Do not make the log level DEBUG or it explodes
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

def get_metrics(days_ago, period=3600, bucket=None, app=None):
    """
    - days_ago: days ago to collect
    - period: metrics period in seconds
    """
    logger.info("Collecting data for %d days ago", days_ago)
    # Firewall args
    if app is None or bucket is None:
        raise ValueError("The 'app' and bucket args must be provided.")
    if not isinstance(days_ago, int) or days_ago <= 0:
        raise ValueError("The 'days_ago' argument must be a positive integer.")

    # Get date in UTC
    date = (datetime.now(dt.timezone.utc) - timedelta(days=days_ago)).date()
    # Set the end time to midnight of the day (00:00:00)
    start_time = datetime.combine(date, dt.time.min)
    end_time = start_time + timedelta(days=1)  # Get data for one day
    logger.info("Collecting data from %s to %s", start_time, end_time)

    # Work out the path to write things to.
    path = f"metrics/year={date.year:04d}/month={date.month:02d}/{date.year:04d}{date.month:02d}{date.day:02d}.csv"

    # Initialize CloudWatch client.
    client = boto3.client('cloudwatch')

    # Namespaces to retrieve metrics from
    namespaces = ["AWS/Lambda", f"{app}/Connect", f"{app}/Check"]

    # Open CSV file for writing; adjust the file name/path as needed.
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)

    # CSV header row
    header = [
        "Namespace",
        "MetricName",
        "Dimensions",
        "Timestamp",
        "Average",
        "Minimum",
        "Maximum",
        "Sum",
        "SampleCount"
    ]
    # Do not write the header, as OpenCSVSerde cannot ignore it.
    #writer.writerow(header)

    # For each namespace, list the metrics and pull out statistics.
    for namespace in namespaces:
        logger.info("Doing namespace %s", namespace)
        paginator = client.get_paginator('list_metrics')
        # Pagination ensures we cover all available metrics
        metrics_iterator = paginator.paginate(Namespace=namespace)

        for page in metrics_iterator:
            metrics = page.get("Metrics", [])
            for metric in metrics:
                logger.debug("Reading metric %s/%s", namespace, metric)
                metric_name = metric.get("MetricName")
                dimensions = metric.get("Dimensions", [])

                # Format dimensions for clearer logging; for instance "Name1=Value1;Name2=Value2"
                dims_str = ";".join([f"{d.get('Name')}={d.get('Value')}" for d in dimensions])

                # Retrieve the metric statistics
                response = client.get_metric_statistics(
                    Namespace=namespace,
                    MetricName=metric_name,
                    Dimensions=dimensions,
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=period,
                    Statistics=["Average", "Minimum", "Maximum", "Sum", "SampleCount"]
                )

                datapoints = response.get("Datapoints", [])
                # Sort the datapoints by timestamp for orderly output
                datapoints.sort(key=lambda dp: dp["Timestamp"])

                for dp in datapoints:
                    # Timestamp format for OpenCSVSerde is integer milliseconds since the epoch.
                    # "timestamp()" returns a float because of course it does.
                    ts = str(int(dp.get("Timestamp").timestamp() * 1000))
                    avg = dp.get("Average", "")
                    mn = dp.get("Minimum", "")
                    mx = dp.get("Maximum", "")
                    s = dp.get("Sum", "")
                    sample = dp.get("SampleCount", "")

                    writer.writerow([
                        namespace,
                        metric_name,
                        dims_str,
                        ts,
                        avg,
                        mn,
                        mx,
                        s,
                        sample
                    ])

    # Write out the CSV buffer
    if bucket is None:
        logger.info("Writing to %s for debug", path)
        with open(path, mode='w') as f:
            print(csv_buffer.getvalue(), file=f)
    else:
        logger.info("Uploading to bucket %s, path %s", bucket, path)
        # Create an S3 client.
        s3 = boto3.client('s3')
        # Upload the CSV data to your S3 bucket.
        s3.put_object(Bucket=bucket, Key=path, Body=csv_buffer.getvalue())

def update_tables(bucket, app):
    """
    Update the athena tables appropriately."
    """
    logger.info("Updating athena configuration")
    if bucket is None:
        logger.info("Bucket is None - drop out")
        return

    # Set up your Athena client
    athena_client = boto3.client('athena')

    # Define parameters
    workgroup_name = f"{app}-athena"

    # Construct the query
    msck_repair_query = f"MSCK REPAIR TABLE {app}.metrics;"

    # Start query execution
    response = athena_client.start_query_execution(
        QueryString=msck_repair_query,
        QueryExecutionContext={
            'Database': app
        },
        WorkGroup=workgroup_name
    )

    query_execution_id = response.get("QueryExecutionId")

    # Poll the query execution status until it's complete. We ignore exceptions and
    # let them bubble up to the top.
    logger.info("Wait for query result")
    state = None
    while True:
        query_status = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
        state = query_status['QueryExecution']['Status']['State']
        if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
            break
        logger.info(f"Query state: {state}. Waiting for completion...")
        time.sleep(1)  # Wait a bit before checking again

    if state == 'SUCCEEDED':
        logger.info("Query succeeded!")
    else:
        error_reason = query_status['QueryExecution']['Status'].get("StateChangeReason", "Unknown error")
        logger.error(f"Query failed with state '{state}'. Reason: {error_reason}")
        raise RuntimeError(f"Query failed with state '{state}'. Reason: {error_reason}")

def lambda_handler(event, context):
    # This reads a range of events from the metrics, and writes them to a CSV file, then points the Athena table at it.
    logger.info("Called with event: %s", event)
    bucket = os.environ["bucket"]
    app = os.environ["app"]

    day_range = event.get("day_range", [1])

    logger.info("Running with bucket: %s, app: %s, range: %s", bucket, app, day_range)
    for days_ago in day_range:
        get_metrics(days_ago=days_ago, bucket=bucket, app=app)

    # Update the tables too
    update_tables(bucket=bucket, app=app)
    logger.info("All done")

    result = {
        "Result": "Success",
        "Inputs": {
            "Bucket": bucket,
            "App": app,
            "Day_range": day_range
        }
    }

    logger.info("Returning structure: %s", result)

    return result

if __name__== "__main__":
    # Called from the command line.
    day_start = int(os.getenv("DAY_START", "1"))
    day_end = int(os.getenv("DAY_END", "3"))

    day_range = list(range(day_start, day_end + 1))
    event = {"day_range": day_range}
    context = {}
    lambda_handler(event, context)
