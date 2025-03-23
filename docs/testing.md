# Testing

This document describes testing that can be done

## Auth testing

TODO: document the test script

## Unit tests

TODO: run automatically, explain how to run manually

## Manual tests of the lambdas

TODO: how to manually trigger testing of lambdas

## End to end testing

A good set of end to end tests to try is the following.

- Call in to the number from an unrecognised number, and validate that you get a sensible message.

- Dial into the number and try to check in / check out. You should get a message saying that there is no matching meeting.

### Mainline

- Dial in and select the `3` (emergency) option. An email should be sent (even though there are no meetings).

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

- Validate that if you leave the meeting for 10 minutes (or manually kick the "CheckFunction" lambda) then:

    - The meeting acquires a `Missed-Check-In` category

    - An email is sent about it.

- Remove the `Missed-Check-In` category, and add a `Checked-In` category as if you checked in.

    - Dial into the number and enter "3". The meeting should acquire an `Emergency` tag, and a mail should be sent.

- Alter the time so the meeting ended at least 15 minutes ago. Validate that if you leave the meeting for 10 minutes (or manually kick the "CheckFunction" lambda) then:

    - The meeting acquires a `Missed-Check-Out` category

    - An email is sent about it.

