# Connect Function

This lambda handles user input, updating the calendar as appropriate.

Appointment lookups use Microsoft Graph's `/calendarView` endpoint so that occurrences of a recurring series are matched and updated individually — the series master and sibling occurrences are never modified.

## Inputs

It is called with two arguments.

- A phone number in E164 format; the literal string "anonymous" if the caller withheld their caller ID (though it guards empty value if run as a manual test).

- A key press from the user, which can take the following values.

    - "1" - check in for an appointment

    - "2" - check out for an appointment

    - "3" - emergency

## Behaviour

The logic for each key press is as follows.

- If the phone number is "anonymous", no directory lookup is attempted (there is nothing to look up):

    - For check in or check out, the caller hears an error message telling them their caller ID was withheld, so they cannot be identified.

    - For emergency, the notification email is still sent as below, recording the calling number as withheld and the caller as unknown.

- For check in or check out:

    - If a calling number was supplied but matches no contact or user account in the directory, tell the caller the number was not recognised; no appointment lookup is attempted.

    - Find the relevant appointment, which must have the correct phone number (i.e. attendee with that mobile number) and a start time (for check in) or end time (for check out) close enough to now. "Close enough" is set by the grace-period values in the configuration - see [config/example.yaml](../../config/example.yaml).

    - If no such appointment or multiple such appointments exist, play an error message to the user asking them to call the office to resolve.

    - Otherwise

        - Add the "Checked-In" or "Checked-Out" category to the appointment.

        - Add a line to the appointment body text indicating the time of the call

- For emergency calls:

    - an email is sent to a configured notification address, whether or not the calling number was recognised; an unrecognised caller is recorded as unknown

    - a benign coded message is played (in case of eavesdropping)

    - if a suitable appointment is found, then the "Emergency" tag is added, and that a line is added to the body indicating that an emergency call was received

## Invocation time limit

The Amazon Connect contact flow, not the Lambda timeout, bounds how long this function has to do all of the above. [resources/LoneWorkerFlow.json](../../resources/LoneWorkerFlow.json) sets `InvocationTimeLimitSeconds` to **8 seconds** for check-in and check-out and **5 seconds** for emergency. Overrunning it means the caller hears the flow's own error prompt instead of any message this function produces.
