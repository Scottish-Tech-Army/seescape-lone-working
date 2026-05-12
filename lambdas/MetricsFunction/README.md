# Metrics Function

This function collects metrics and stores them in the S3 bucket so as to allow access.

It takes an event structure a single `day_range` argument, which is an array of the number of days to do (so if the array was `[1,2,3]` it would collect data for 1, 2, and 3, days ago). It then kicks the AWS Athena configuration to reindex its data.

`0` is a valid value in `day_range` and means today: the query covers the full UTC day, so CloudWatch returns only the populated datapoints so far and you get a partial-day snapshot. Re-running for the same day overwrites the S3 object. This is intended for manual testing on a test rig — cron always passes 1 or more.

When called by cron, it is called twice.

- At 01:00 it is called to process the previous day's metrics.

- At 02:00 it is called again, to kick Athena again (without collecting metrics). There is a timing window where sometimes Athena may not notice newly created data in its database, and this fixes that issue if it occurs.
