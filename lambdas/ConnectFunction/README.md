# Connect Function

This lambda handles user input, updating the calendar as appropriate.

It is called with two arguments.

- A user identifier. *TODO: update when this becomes automatically provided*

- A key press from the user, which can take the following values.

    - "1" - check in for an appointment

    - "2" - check out for an appointment

    - "3" - emergency

The logic for each of these is as follows.

- For check in or check out:

    - Find the relevant appointment, which must have the correct user ID and a time (start time for check in, end time for check out) within a window from 30 minutes ago to 30 minutes in the future.

    - If no such appointment or multiple such appointments exist, play an error message to the user asking them to call the office to resolve.

    - Otherwise

        - Add the "Checked-In" or "Checked-Out" category to the appointment.

        - Add a line to the appointment body text indicating the time of the call

- For emergency calls:

    - an email is sent to a configured notification address

    - a benign coded message is played (in case of eavesdropping)

    - if a suitable appointment is found, then the "Emergency" tag is added, and that a line is added to the body indicating that an emergency call was received

