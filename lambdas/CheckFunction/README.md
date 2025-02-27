# Check Function

This function performs the check capability. It is triggered every 15 minutes to find lone workers who have checked in but not checked out, or who failed to check out from an appointment after checking in.

The flow is as follows.

- Log into the configured calendar

- Find missed checkins by finding all appointments matching the following

    - The start time is at least 15 minutes in the past (since we are letting users be 15 minutes late before we trigger an alarm)

    - The start time is no more than 75 minutes in the past (so that we are not processing very old appointments needlessly; every appointment has four opportunities to be caught by the tool).

    - The appointment has not been checked in (there is no "Checked-In" category on the appointment).

    - The issue has not been already successfully flagged (there is no "Missed-Check-In" category on the appointment).

- Find missed checkouts by finding all appointments matching the following

    - The end time is at least 15 minutes in the past (again, 15 minutes grace).

    - The end time is no more than 75 minutes in the past (again, to avoid catching ancient appointments).

    - The appointment has not been checked out (there is no "Checked-Out" category on the appointment).

    - The issue has not been already successfully flagged (there is no "Missed-Check-Out" category on the appointment).

For each missed checkin or checkout, the following process is followed.

- An email is sent (from the central user account owning the calendar) to a configured address reporting the issue.

- The appointment is modified to have a category "Missed-Check-In" or "Missed-Check-Out" as appropriate, so it will not be flagged again.
