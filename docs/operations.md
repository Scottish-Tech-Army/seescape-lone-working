# Installation process

*This is very much a work in progress; some basic notes.*

## Prerequisites

- AWS subscription to use

- M365 email account with calendar to use; will send email and show calendar

    - Must create an app in the M365 tenant to allow logins (details to be provided)

    - Some parameters from the above:

        - Tenant GUID

        - ClientID and ClientSecret for the app

        - Email address and password

- Config files - example is `plw_env.sh`

    - *Some documentation in the example file, needs beefing up*

## Initial creation only

### Run scripts to deploy resources

- Go to the root directory of the repository

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

    *This reports a spurious error - ignore it until fixed.*

~~~bash
bash scripts/lambdas.sh
~~~

- Deploy the lambdas using code formation. This deploys the lambdas and also various IAM configuration.

    *This is separate from initial.sh for no good reason; should combine them in due course.*

~~~bash
bash scripts/lambdas.sh
~~~

### Update secrets

*This process could be automated but is not for security reasons; we do not want passwords or IDs in config files.*

Update the secrets to have the correct values as follows.

- Go to the AWS console in a web browser.

- Find the "AWS Systems Manager/Parameter Store" - this can be found by entering `Parameter Store` in the search box.

- For each of the five parameters, enter the correct value.

    *Details of values and parameters to be provided.*

### Configure Amazon Connect

*AWS Connect is deployed at this point, but needs configuration.*

Needs at the very least 

- add a number

- add the relevant flow, including lambdas etc.

- set up routing

- configure prompts

## Validation

*Some level of test and validation*

# Upgrading to new version of code

*In principle just running build.sh, but the script needs cleaning up.*

# Other operational processes

## Burndown

*xxx - how do we get to a clean state afterwards*

## Backup

*xxx - do we need a backup strategy? We may not need one if everything is reproducible in code*

# Logs / metrics / whatever ...

*xxx*