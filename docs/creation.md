# Initial installation

This document specifies how to perform initial installation. It assumes that you have set up all the [prerequisites requirements](prereqs.md).

## Run scripts to deploy resources

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

- Build and push the code. *This reports that it is ignoring some lambdas that do not exist yet - this is benign.*

~~~bash
bash scripts/code_build.sh notest
bash scripts/code_push.sh
~~~

- Deploy the lambdas using code formation. This deploys the lambdas and also various IAM configuration.

~~~bash
bash scripts/lambdas.sh
~~~

All the resources now exist, but there is still configuration to do.

### Update secrets

*This process could be automated but is not for security reasons; we do not want passwords or IDs in config files.*

Update the secrets to have the correct values as follows.

- Go to the AWS console in a web browser.

- Find the "AWS Systems Manager/Parameter Store" - this can be found by entering `Parameter Store` in the search box.

- For each of the five parameters, enter the correct value.

    *TODO: Details of values and parameters to be provided.*

### Configure Amazon Connect

This is largely done by script.

~~~bash
bash scripts/lambdas.sh
~~~

Once you have done that you must manually assign a phone number in the AWS Connect GUI. You can find this as follows.

- Go to the AWS Console

- Enter `Connect` in the search bar, select the Connect service, and select your AWS Connect instance.

- Click `Log in for emergency access`

Now go through each of the following steps.

- On the left, select `Phone numbers` under `Channels`. You can then pick a phone number and assign it to the loneworker flow.

*TODO: This does not work - there is some kind of quota issue. The workaround appears to be to request a quota increase.*

### Set up dashboards

This could be automated better, but a basic dashboard can be created as follows.

~~~bash
aws cloudwatch put-dashboard --dashboard-name "loneworker" --dashboard-body file://resources/dashboard.json
~~~

## Validation

*TODO: Some level of test and validation*



