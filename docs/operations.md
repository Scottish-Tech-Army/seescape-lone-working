# Operations processes

This document covers operational tasks for a deployed instance: alert configuration, client secret rotation, upgrading to a new code version, routine monitoring, and cost expectations.

## Alert configuration

CloudWatch alarms are configured for Lambda errors and throttles on the Connect and Check functions. When any of these alarms fires, it publishes to an SNS topic named `${APP}-alerts` (normally `loneworker-alerts`). The topic is created automatically when you run `bash scripts/lambdas.sh`; you only need to add subscribers. Email subscribers to that topic are notified.

You should subscribe at least one human inbox - typically the support engineer - so that errors are not missed. The shared mailbox can also be subscribed if desired, though this should be considered carefully to avoid noise.

Subscriptions are not managed in CloudFormation; they are added in the AWS console and persist across stack updates.

To subscribe an email address:

- Go to the AWS console and find SNS (enter `SNS` in the search bar).

- Select `Topics` on the left, then click the `${APP}-alerts` topic.

- Click `Create subscription`.

- Set `Protocol` to `Email` and `Endpoint` to the address you want to notify.

- Click `Create subscription`.

- The recipient will receive a confirmation email from AWS. They must click the link in that email before notifications will be delivered.

To remove a subscriber, find the subscription in the same topic and delete it.

## Client secret rotation

The M365 client secret has a finite lifetime (the Entra default is three months, and the value must be no more than one year). When the secret expires, every Lambda call to Microsoft Graph fails and the application stops working. This section covers how to rotate the secret before that happens.

### When to rotate

You will be notified by email when one of three CloudWatch alarms fires:

- `Client Secret Expiring Within Month` — fires roughly 30 days before the recorded expiry date. Plan a rotation in the next week or two.
- `Client Secret Expiring Within Week` — fires 7 days before expiry, or on/after expiry. Rotate now.
- `Client Secret Expiry Invalid` — fires when the recorded expiry date is missing, unparseable, or set more than a year ahead. This usually means the date in Parameter Store has not been set, or was entered in the wrong format. Set it to the real expiry date as shown in Entra (see "Update Parameter Store" below).

The dashboard also shows the current days-until-expiry as a single-value widget next to the routine operations panel. You can sanity-check at any time without waiting for an alarm.

### Create a new secret in Entra

- Go to the [Entra Admin Centre](https://entra.microsoft.com).

- Navigate to `Applications` → `App Registrations`, and find your application (the one named when you originally followed the [prerequisites](prereqs.md#application)).

- Open the application and select `Certificates & secrets` on the left.

- Click `New client secret`.

- Fill in the description (something like `loneworker rotation YYYY-MM` so future operators can tell secrets apart) and pick an expiry of up to one year, and at least three months. Click `Add`.

- A new entry appears in the list of client secrets. **Copy the `Value` column immediately** — once you leave or refresh the page it is gone forever and you must create another secret.

    *⚠️ The list shows two columns, `Value` and `Secret ID`. You want the **Value**. The Secret ID is just an internal identifier and will not authenticate.*

- Note the `Expires` date shown in the list. You will need this in ISO 8601 (`YYYY-MM-DD`) form below.

- Optionally, delete the old client secret entry from the list. Alternatively, leave it until it expires (it stops working at that point anyway). A safer order is to leave the old one in place until you have confirmed the new one is working in Parameter Store, then delete it.

### Update Parameter Store

- Go to the AWS console and find Parameter Store (enter `Parameter Store` in the search bar).

- Update `/${APP}/clientsecret` with the new secret value you just copied.

- Update `/${APP}/clientsecretexpiry` with the expiry date in ISO 8601 form (`YYYY-MM-DD`). For example: `2028-05-06`.

- Within ten minutes the next `CheckFunction` invocation will pick up the new values and report a fresh days-to-expiry metric. The expiring/invalid alarms will transition back to `OK` shortly after that.

### Verify

- Wait up to 25 minutes for the alarms to clear: 10 minutes for the next CheckFunction run plus a single 15-minute CloudWatch alarm evaluation period. The dashboard widget reflects the metric within a few minutes; the alarm state takes one more period to flip. (The three client-secret alarms use a single evaluation period rather than the 12-hour window used by the legacy lambda/throttle alarms as they are reflecting current state rather than past errors.)

- On the dashboard, confirm the "Days until expiry" widget reports a value consistent with the new expiry date.

- Make a test call (per the [test guide](testing.md)) to confirm authentication still works end-to-end with the new secret.

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

- At the top of the dashboard, the **Meeting outcomes and incidents** banner gives the three meeting outcomes at a glance, alongside emergency calls and lambda errors/throttles. Every meeting tracked by the application ends in exactly one of these three outcomes:

    - **Meetings completed OK** — a lone worker successfully checked in and then checked out. Incremented once per meeting, not once per call, so a repeat-checkout call does not double-count.

    - **Checkins missed** — the meeting started but no checkin call ever arrived (the `CheckFunction` background scan detected this and sent a warning email).

    - **Checkouts missed** — the worker checked in but never checked out.

    A healthy day should be dominated by "Meetings completed OK"; the two "missed" counters should normally be zero or very small.

- You should also be able to find logs for all calls to the lambda functions.

### Costs

This costs money to run. Roughly the cost implications are as follows.

- There is no additional cost to the M365 tenant; shared mailboxes are free, and so are emails.

- AWS costs are a little more complicated.

    - If *provisioned concurrency* is used (i.e. the `CONCURRENCY` value is set non-zero in the config file), then the cost is around $15 per month times the value. If set to zero, then the cost is negligible.

    - Each phone call incurs a cost of $0.038 per minute (minimum billing period one minute). If you have 5 staff who make 20 calls per week, and are taking the cost of having a freephone number, then that is around $16 per month.

    - There are other costs for storage, configuration and so on. These are low enough to be insignificant compared to the above two.

    In practical terms, the cost of a customer who has around 10-20 meetings per week has historically been $8 to $10 including tax.


