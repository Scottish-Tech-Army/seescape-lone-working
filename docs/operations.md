# Operations processes

*This is still rather basic, but gets the key ideas across.*

## Upgrading to new version of code

In order to take a new version of the code, you should follow the process below.

- Check out the code from the [github repo](https://github.com/Scottish-Tech-Army/seescape-lone-working), and `cd` into the root directory.

- Load your config file.

    ~~~bash
    . config/whatever_env.sh
    ~~~

- Build and push your code

    ~~~bash
    bash scripts/code_build.sh test && bash scripts/code_push.sh
    ~~~

- Validate that the code is working manually, following the [test guide](testing.md).

## Routine operations

### Monitoring

You can find logs, dashboards and metrics under CloudWatch.

- Log into the AWS console.

- Go to CloudWatch (enter `CloudWatch` in the search bar if necessary).

- The dashboard is named with the value of `${APP}`, which is normally `loneworker`. This shows how many calls to the Lambda functions of different types have occurred.

- You should also be able to find logs for all calls to the lambda functions.

### Costs

This costs money to run. Roughly the cost implications are as follows.

- There is no additoinal cost to the M365 tenant; shared mailboxes are free, and so are emails.

- AWS costs are a little more complicated.

    - In AWS the predominant cost is that of the lambda function running with provisioned concurrency. If the provisioned concurrency is set to 1 in configuration (as recommended), then the cost is around $15 (so perhaps £12) per month.

    - Each phone call incurs a cost of $0.038 per minute (minimum billing period one minute). If you have 5 staff who make 20 calls per week, and are taking the cost of having a freephone number, then that is around $16 per month - so very comparable to the cost of the lambda provisioning.

    - There are other costs for storage, configuration and so on. These are low enough to be insignificant compared to the above two.

