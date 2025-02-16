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

- Go to the root directory of the repository

- Load the config for the environment, and run the script `initial.sh`, which deploys various initial resources.

    - The configuration parameters for credentials.

    - The S3 bucket for all resources.

    - The Amazon Connect instance itself.

~~~bash
. config/whatever_env.sh
bash initial.sh
~~~

- Update the secrets to have the correct values.

    - *xxx describe that here - deliberately not automated for better security*

## Deploy lambdas

*This is separate from initial.sh for no good reason; should combine them in due course.*

- Deploy the lambdas using code formation. This deploys the lambdas and also various IAM configuration.

~~~bash
. config/whatever_env.sh
bash lambdas.sh
~~~

## Build lambdas

This can be done multiple times for new code releases

- Build and deploy the lambda code to S3

    *This is a little poor, in that there are undocumented parameters in that script. The name is also somewhat misleading, as it deploys as well as builds.*

~~~bash
. config/whatever_env.sh
bash build.sh
~~~

## Configure Amazon Connect

*AWS Connect is deployed at this point, but needs configuration.*

Needs at the very least 

- add a number

- add the relevant flow, including lambdas etc.

- set up routing

- configure prompts

## Validation

*Some level of test and validation*

# Upgrading to new version of code

*Going to amount to redeploying the lambdas after changing the code, as per above.*

*Something about how to upgrade / reconfigure Amazon Connect too*

# Other operational processes

## Burndown

*xxx - how do we get to a clean state afterwards*

## Backup

*xxx - do we need a backup strategy? We may not need one if everything is reproducible in code*

# Logs / metrics / whatever ...

*xxx*