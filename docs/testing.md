# Testing

This document describes testing that can be done.

## Unit tests

There are some unit tests which run automatically when you run the following.

~~~bash
bash scripts/build_code.sh test
~~~

These report output to screen. If you just want to test a subset of tests, then you can run something like this.

~~~bash
cd lambdas/ConnectFunction/tests
pytest -o log_cli=true -o log_cli_level=info
~~~

## Validating credentials

Once you have set up all of the M365 tenant information, it is very useful to test it all in isolation. The script [test_creds.py](../scripts/test_creds.py) will allow this. It can be run as follows.

- Set up required environment variables for the script.

    ~~~bash
    export CLIENT_ID="client id"
    export CLIENT_SECRET="client secret"
    export TENANT_ID="tenant id"
    export USERNAME="shared mailbox email"
    ~~~

- If required install the various modules; exact syntax will depend on your install.

    ~~~bash
    pip install requests
    pip install urllib
    pip install pyjwt
    ~~~

- Run the script.

    ~~~bash
    python scripts/test_creds.py
    ~~~

You should see the script running cleanly, reporting data to screen. If there are any errors, they will be reported, and you can figure out what is wrong; it should be fairly obvious whether it is a failed login, failure to read particular data or whatever.

## Validating the lambda functions

This checks that the lambda functions are doing what they should be doing, without going through full end to end testing.

- Log into the AWS console, and find Lambda functions (enter `lambda` in the search bar if necessary).

- To validate the `check` function works:

    - Select `CheckFunction`

    - Click the `Test` button

    - Ensure that the response looks reasonable, and check the logs (linked to from that page)

    - Repeat after setting up some meetings that should trigger mails (obviously, make sure you do not cause a panic when you do this).

- To validate the `connect` function works:

    - Select `ConnectFunction`

    - Set up three inputs (if they do not already exist). These can all look something like the example below - with "buttonpressed" taking the value 1, 2, 3 for checkin / checkout / emergency. For most test cases, you should ensure that the mobile number matches a real mobile number, [as documented in the user instructions](user.md#configuring-user-accounts).

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

## End to end testing

*End to end testing assumes that you exist with the correct mobile phone number in the M365 client, [as documented in the user instructions](user.md#configuring-user-accounts), and also that you have access to the shared mailbox to check what is happening.*

A good set of end to end tests to try is the following.

### Tyre kicking

- Call in to the number from an unrecognised number, and validate that you get a sensible message.

- Dial into the number and try to check in (`1` option). You should get a message saying that there is no matching meeting.

- Dial into the number and try to check out (`2` option). You should get a message saying that there is no matching meeting.

- Dial in and select the `3` (emergency) option. An email should be sent (even though there are no meetings).

### Mainline

- Create two meetings starting around now, one with your number and one with another.

    - Dial into the meeting to check in. The meeting should acquire a `Checked-In` category.

    - Dial in to check in again (you should get an "already checked in" message)

    - Try to check out - it should fail (you are likely to be too early)

- Alter the meeting timing so that you can check out (i.e. get the end of the meeting to within 30 minutes of current time).

    - Dial in and check out. The meeting should acquire a `Checked-Out` category.

    - Dial in and check out. This should explain that the meeting is already checked out.

    - Remove the checkin and checkout categories, then try to checkout again - it should fail as you have not checked in.

- Set up two back to back meetings with the changeover being the current time. Mark the first as `Checked-In` and then check into the second.

    - You should see that the older meeting gets a `Checked-In` as well as the newer one getting a `Checked-Out`

    - Try to check in again, and make sure that you get an "already checked out" message.

    - Make sure you can check out of the second meeting.

### Emergencies

- Validate that if you leave the meeting without any categories until the start is at least 15 minutes in the past then after 10 minutes (or manually kick the `CheckFunction` lambda):

    - The meeting acquires a `Missed-Check-In` category (but not a `Missed-Check-Out`)

    - An email is sent about it.

    - Kick the `CheckFunction` lambda again; you should not get another mail.

- Remove the `Missed-Check-In` category, add a `Checked-In` category as if you checked in, and set the meeting so it ended in the past half hour.

    - Dial into the number and enter `3`. The meeting should acquire an `Emergency` tag, and a mail should be sent.

- Alter the time so the meeting ended at least 15 minutes ago. Validate that if you leave the meeting for 10 minutes (or manually kick the `CheckFunction` lambda) then:

    - The meeting acquires a `Missed-Check-Out` category

    - An email is sent about it.

