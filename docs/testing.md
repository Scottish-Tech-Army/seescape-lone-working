# Testing

This document describes testing that can be done. It covers the following.

1. [Unit tests](#unit-tests).

2. [Validating M365 credentials](#validating-credentials) in isolation.

3. [Per-Lambda validation](#validating-the-lambda-functions) in the AWS console.

4. [The end-to-end test plan](#end-to-end-test-plan), including a dedicated subsection for [recurring meetings](#recurring-meetings).

## Unit tests

There are some unit tests which run automatically when you run the following (after sourcing your environment variables in config).

~~~bash
bash scripts/code_test.sh
~~~

These report output to screen. If you just want to test a subset of tests, then you can run something like this.

~~~bash
cd lambdas/ConnectFunction/tests
pytest -o log_cli=true -o log_cli_level=info
~~~

*These tests are frankly a little limited; they do not report code coverage and could be more complete, but they should always run clean if a change has not broken anything.*

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

- To validate the `check` function (which performs routine checks for missed checkins and checkouts):

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

- To validate the `metrics` function works:

    - Select `MetricsFunction`

    - Set up an input file. An example (that collects for one and two days in the past) is given below.

        ~~~json
        {
            "day_range": [1, 2]
        }
        ~~~

    - Click the `Test` button

    - Ensure that the response looks reasonable.

## End to end test plan

*End to end testing assumes that you exist with the correct mobile phone number in the M365 client, [as documented in the user instructions](user.md#configuring-user-accounts), and also that you have access to the shared mailbox to check what is happening.*

To get a good level of end to end testing, follow the test cases below. Unless otherwise stated, use the lone worker shared mailbox to create meetings.

### Tyre kicking

- Call in to the number from an unrecognised number, and validate that you get a sensible message.

- Dial into the number and try to check in (`1` option). You should get a message saying that there is no matching meeting.

- Dial into the number and try to check out (`2` option). You should get a message saying that there is no matching meeting.

- Dial in and select the `3` (emergency) option. An email should be sent (even though there are no meetings).

### Mainline

- Create two meetings starting around now, one with your number and one with another (as invited members).

    - Dial into the meeting to check in. The meeting should acquire a `Checked-In` category.

    - Dial in to check in again. You should get an "already checked in" message.

    - Try to check out - it should work, even though the meeting has only just started. The meeting should acquire a `Checked-Out` category.

    - Dial in and check out again. You should get an "already checked out" message.

    - Remove the checkin and checkout categories, then try to checkout again. You should get an error saying you have not checked in.

- Set up two back to back meetings with the changeover being the current time. Mark the first as `Checked-In` (not `Checked-Out`) and then check into the second.

    - You should see that the older meeting gets a `Checked-Out` as well as the newer one getting a `Checked-In`

    - Try to check in again, and make sure that you get an "already checked in" message.

    - Call in to check out. This should succeed.

- Set up two back to back meetings with the changeover being the current time. Mark the first as `Checked-In` (not `Checked-Out`).

    - Check out and check that the first meeting is checked out.

    - Check in and see that the second meeting is checked in now.

    - Check out and see that both meetings are now checked out.

### Emergencies and missed calls

- Validate that if you leave the meeting without any categories until the start is at least 15 minutes in the past then after 10 minutes (or manually kick the `CheckFunction` lambda):

    - The meeting acquires a `Missed-Check-In` category (but not a `Missed-Check-Out`)

    - An email is sent about it.

    - Kick the `CheckFunction` lambda again; you should not get another mail.

- Remove the `Missed-Check-In` category, add a `Checked-In` category as if you checked in, and set the meeting so it ended in the past half hour.

    - Dial into the number and enter `3`. The meeting should acquire an `Emergency` tag, and a mail should be sent.

- Alter the time so the meeting ended at least 15 minutes ago. Validate that if you leave the meeting for 10 minutes (or manually kick the `CheckFunction` lambda) then:

    - The meeting acquires a `Missed-Check-Out` category

    - An email is sent about it.

### Recurring meetings

These tests check that recurring meetings are handled correctly: each occurrence in a series should be treated as its own appointment, and any category or body change should affect only that occurrence — not the series master, and not sibling occurrences.

The prerequisites for these tests are the same as the end-to-end plan above (real mobile registered, shared-mailbox access). Several tests also require you to invoke `CheckFunction` manually from the AWS Lambda console — see [Validating the lambda functions](#validating-the-lambda-functions) above for how.

For setup, "daily recurring meeting" means a series whose recurrence pattern is daily. A daily cadence is convenient for testing because today's and tomorrow's occurrences are easy to inspect side-by-side; the same behaviour applies to weekly or monthly cadences.

After every step that mutates a meeting, inspect both the **series master** (the original recurring event) and at least one **sibling occurrence** (e.g. tomorrow's) in Outlook to confirm they are unmodified, in addition to checking the targeted occurrence.

#### Check-in and check-out on a current occurrence

- Create a daily recurring meeting that started yesterday at the current time of day (so today's occurrence is starting around now), runs for an hour, and recurs daily for at least three more days. Add your phone number's email address as the only attendee.

    - Dial in to check in (`1` option). The call should succeed.

    - Confirm that **today's occurrence only** has the `Checked-In` category. The series master and tomorrow's occurrence should be unmodified.

    - Dial in to check in again — you should get an "already checked in" message.

    - Dial in to check out (`2` option). The call should succeed.

    - Confirm that today's occurrence now has both `Checked-In` and `Checked-Out`, and that the series master and tomorrow's occurrence are still unmodified.

    - Dial in to check in again — you should get an "already checked out" message.

    - Dial in to check out again — you should get an "already checked out" message.

#### Missed check-in on a recurring occurrence

- Create a daily recurring meeting that started yesterday at a time of day that is now between 15 and 75 minutes ago (so today's occurrence falls in the missed-check-in window). Include your phone number's email as the only attendee. Do not check in.

    - Wait for the next `CheckFunction` run, or kick it manually.

    - Today's occurrence should acquire a `Missed-Check-In` category. The series master and tomorrow's occurrence should not.

    - A mail should be sent.

    - Kick `CheckFunction` again; you should not get another mail.

#### Missed check-out on a recurring occurrence

Note: Outlook's GUI only lets you edit categories on the entire series, not on a single occurrence, so the setup uses the tooling itself to put `Checked-In` on a single occurrence and then drags the occurrence in Outlook (which is per-occurrence) to push the end time into the missed-checkout window.

- Create a fresh daily recurring meeting whose current occurrence's start time is now (so it falls in the check-in window). Include your phone number's email as the only attendee.

    - Dial in to check in. Today's occurrence acquires `Checked-In`. The series master and tomorrow's occurrence should be unmodified.

    - In Outlook, drag *just today's occurrence* so it now starts about an hour ago and ends about 30 minutes ago (firmly inside the missed-checkout window of 15–75 minutes after the end time).

    - Wait for `CheckFunction` to run, or kick it manually.

    - Today's occurrence should acquire a `Missed-Check-Out` category. The series master and tomorrow's occurrence should not.

    - A mail should be sent.

#### Emergency on a recurring occurrence

- Create a daily recurring meeting whose current occurrence is in progress now. Include your phone number's email as the only attendee.

    - Dial in and select `3` (emergency).

    - An emergency mail should be sent.

    - Today's occurrence should acquire an `Emergency` category. The series master and tomorrow's occurrence should not.

#### Rescheduled occurrence

- Create a daily recurring meeting whose master time of day is one hour ago, so today's occurrence as originally scheduled is now outside the check-in window. In Outlook, drag today's occurrence so it now starts around the current time. Include your phone number's email as attendee.

    - Dial in to check in. The call should succeed and the rescheduled occurrence should acquire `Checked-In`. The series master and the other occurrences should be unmodified.

#### Cancelled occurrence

- Create a daily recurring meeting whose master time of day is the current time of day. In Outlook, cancel just today's occurrence (delete it from the series — do not delete the whole series). Include your phone number's email as attendee.

    - Dial in to check in. You should get a "no matching appointment" message — the cancelled occurrence must not be matched, and the tooling must not fall back to matching the series master.

#### Mixed: recurring series alongside a one-off meeting

- With a daily recurring series in progress now (as set up in the first test above), additionally create a single-instance meeting at the same time with a different attendee (someone else's email).

    - Dial in to check in. The recurring series's current occurrence should be checked in; the single-instance meeting must remain unmodified.

#### Edit-series footgun

This documents an Outlook-side behaviour that the tooling cannot prevent: editing a recurring series's *non-category* properties (time, subject, attendees, …) silently wipes per-occurrence categories that the tooling has set, leaving no record that a check-in or check-out had happened. This test pins the behaviour so future regressions are caught.

*Background: the underlying Graph/Outlook semantics are asymmetric — a series-level category edit respects per-occurrence exceptions, while a series-level edit of any other property does not. The user-facing summary is simply that editing a recurring series can clobber tooling-set state on its occurrences.*

- Reuse the daily recurring meeting from the first test in this section, after both check-in and check-out have run (so today's occurrence carries `Checked-In` and `Checked-Out`).

    - In Outlook, edit the series — change something other than categories (e.g. the subject, or the time of day) and save with "all events in the series".

    - Re-inspect today's occurrence: the `Checked-In` and `Checked-Out` categories should have been wiped. This is expected Outlook behaviour, not a tooling bug.

    - Confirm that the tooling itself was not involved (no Connect/Check Lambda invocation in CloudWatch around the edit time). The category change came purely from Outlook's series-edit semantics.
