# Initial installation

This document specifies how to perform initial installation, in four stages.

1. [Deploy AWS resources](#run-scripts-to-deploy-resources).

2. [Populate secrets in Parameter Store](#update-secrets).

3. [Configure Amazon Connect and assign a phone number](#configure-amazon-connect).

4. Optionally [enable metrics export](#enable-metrics-export).

It assumes that you have completed the [prerequisites](prereqs.md), and that each script in this document reports success and returns zero; if any does not, the deployment has failed and you should stop and diagnose before continuing.

## Run scripts to deploy resources

This step deploys the main resources you will be using.

- Check out the repository, and change directory to the root of the repository

- Source the config for the environment. All scripts in this section assume that this has been done.

    ~~~bash
    . config/whatever_env.sh
    ~~~

- Run the script `initial.sh`, which deploys various initial resources.

    - The configuration parameters for credentials.

    - The S3 bucket for all resources.

    - The Amazon Connect instance itself.

    ~~~bash
    bash scripts/initial.sh
    ~~~

- Build and push the code.

    ~~~bash
    bash scripts/code_build.sh notest
    bash scripts/code_push.sh
    ~~~

- Deploy the lambdas using Cloud Formation. This deploys the lambdas, lots of IAM configuration, and the management dashboard.

    ~~~bash
    bash scripts/lambdas.sh
    ~~~

- Subscribe at least one email address to the alert SNS topic so that errors are noticed. Follow the [alert configuration instructions](operations.md#alert-configuration).

## Update secrets

*This process could be automated but is not for security reasons; we do not want passwords or IDs in config files.*

Update the secrets to have the correct values as follows.

- Go to the AWS console in a web browser.

- Find the "AWS Systems Manager/Parameter Store" - this can be found by entering `Parameter Store` in the search box.

- For each of the five parameters, enter the correct value (all of which you should have noted down during the prerequisites stage).

    - `/${APP}/tenant`: Tenant ID, the GUID for your organisation
    - `/${APP}/clientid`: Client ID for the M365 application, a GUID
    - `/${APP}/clientsecret`: Client secret for the M365 application — the **secret value**, not the secret ID. (Sigh.)
    - `/${APP}/clientsecretexpiry`: The expiry date of the client secret as ISO 8601 (`YYYY-MM-DD`), as shown in Entra. Stored as a plain `String` (the date is not sensitive). Until this is set to a real date, the `Client Secret Expiry Invalid` alarm will fire.
    - `/${APP}/emailuser`: Email address of the shared mailbox

    *Client secrets expire periodically. When that approaches, you will receive an alert email; follow the [client secret rotation procedure](operations.md#client-secret-rotation) to refresh both `clientsecret` and `clientsecretexpiry`.*

## Configure Amazon Connect

This is largely done by script.

~~~bash
bash scripts/connect.sh
~~~

Once you have done that you must manually assign a phone number in the AWS Connect GUI. You can find this as follows.

- Go to the AWS Console

- Enter `Connect` in the search bar, select the Connect service, and select your AWS Connect instance.

- Click `Log in for emergency access`

- Find the entries that link to AWS Lambda functions, and reselect the Lambda function (which ensures that permissions are updated for these Lambdas).

- Click `save`, then `publish`.

- On the left, select `Phone numbers` under `Channels`.

    - Select a phone number.

    - Assign it to the loneworker flow.

If you call the assigned phone number, you should find that the call is answered.

## Enable metrics export

*This section is optional - if you are not going to export your metrics into an external BI solution, you can skip it.*

Metrics are exposed in an Athena database which can be connected to an external BI solution.

- Set up the Athena database as follows.

    ~~~bash
    bash scripts/athena.sh
    ~~~

- In order to expose this database, you need a SQL alchemy string. You can generate one as follows.

    ~~~bash
    bash scripts/create_sql_alchemy.sh
    ~~~

    This reports output something like this.

    ~~~
    Using region: eu-west-2
    Access Key ID found OK
    Secret access Key ID found OK

    Encoded key follows on next line:
    awsathena+rest://ACCESS_KEY_ID:ENCODED_KEY@athena.REGION.amazonaws.com/loneworker?s3_staging_dir=s3://BUCKET_NAME/metrics/&work_group=loneworker-athena"
    ~~~

