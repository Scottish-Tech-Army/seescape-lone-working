# Operations processes

*This is still rather basic, but gets the key ideas across.*

## Upgrading to new version of code

In order to take a new version of the code, you should follow the process below.

- Check out the code from the [github repo](https://github.com/Scottish-Tech-Army/seescape-lone-working), and `cd` intot he root directory.

- Load your config file.

    ~~~bash
    . config/whatever_env.sh
    ~~~

- Build and push your code

    ~~~bash
    bash scripts/code_build.sh test && bash scripts/code_push.sh
    ~~~

- Validate that the code is working manually.

    - Log into the AWS console, and find Lambda functions (enter `lambda` in the search bar if necessary).

    - To validate the `check` function works:

        - Select `CheckFunction`

        - Click the `Test` button

        - Ensure that the response looks reasonable, and check the logs (linked to from that page)

        - Repeat after setting up some meetings that should trigger mails (obviously, make sure you do not cause a panic when you do this).

    - To validate the `connect` function works:

        - Select `ConnectFunction`

        - Set up three inputs (if they do not already exist). These can all look something like the example below - with "buttonpressed" taking the value 1, 2, 3 for checkin / checkout / emergency. You should ensure that the mobile number matches a real mobile number.

        ~~~json
        {
        "Details": {
            "Parameters": {
            "buttonpressed": "1"
            },
            "ContactData": {
            "CustomerEndpoint": {
                "Address": "+447123123456"
            }
            }
        }
        }
        ~~~

        - Click the `Test` button

        - Ensure that the response looks reasonable, and check the logs (linked to from that page)

        - Set up some real meetings and make sure that checkin / checkout / emergency calls work.

## Monitoring

You can find logs, dashboards and metrics under CloudWatch.

- Log into the AWS console.

- Go to CloudWatch (enter `CloudWatch` in the search bar if necessary).

- You should see a dashboard (the `loneworker` dashboard) with metrics.

- You should also be able to find logs for all calls to the lambda functions.
