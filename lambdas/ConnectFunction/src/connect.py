import requests
from datetime import datetime
import os

import loneworker_utils as utils

KEY_CHECK_IN="1"
KEY_CHECK_OUT="2"
KEY_EMERGENCY="3"

METRIC_CHECKINS = "Checkins"
METRIC_CHECKOUTS = "Checkouts"
METRIC_EMERGENCY = "Emergencies"
METRIC_UNKNOWN_CALLER = "UnknownCaller"
METRIC_APPT_NOT_FOUND = "NoMatchingAppointment"
METRIC_DUPLICATE_CALL = "DuplicateCall"
METRIC_SUCCESS = "Success"

ALL_METRICS = [
    METRIC_CHECKINS,
    METRIC_CHECKOUTS,
    METRIC_EMERGENCY,
    METRIC_UNKNOWN_CALLER,
    METRIC_APPT_NOT_FOUND,
    METRIC_DUPLICATE_CALL,
    METRIC_SUCCESS,
]

logger = utils.get_logger()

def get_calendar(manager, action, addresses, end_before=None):
    """
    Get Calendar items from the MS Graph API

    This code reads relevant events from the calendar of the configured user and returns them in an array.

    If passed an explicit "end_before" (a UTC dateTime string from the graph API) then add to the usual
    logic a test that the meeting end time is before (or equal to) that time.
    """
    logger.info("Get calendar events - action %s, end_before %s", action, end_before)
    app_cfg = manager.get_app_cfg()

    checkin_grace_min = app_cfg["checkin_grace_min"]
    checkout_grace_min = app_cfg["checkout_grace_min"]
    ignore_after_min = app_cfg["ignore_after_min"]

    time_filters = []
    if action == KEY_CHECK_IN:
        # Look for a meeting due to start between 15 minutes ago and 15 minutes in the future (actually checkin_grace_min)
        time_filters.append(utils.TimeFilter(minutes=-checkin_grace_min, before_or_after=utils.AFTER, start_or_end=utils.START))
        time_filters.append(utils.TimeFilter(minutes=checkin_grace_min, before_or_after=utils.BEFORE, start_or_end=utils.START))
    elif action == KEY_CHECK_OUT:
        # Look for a meeting due to end between 15 minutes ago and 75 minutes in the future (actually checkout_grace_min and ignore_after_min)
        # We may catch multiple meetings with this check, because it is overbroad, but we are allowing early checkout, and distinguishing
        # which of the multiple matches has been checked in and not checked out
        time_filters.append(utils.TimeFilter(minutes=-checkout_grace_min, before_or_after=utils.AFTER, start_or_end=utils.END))
        time_filters.append(utils.TimeFilter(minutes=ignore_after_min, before_or_after=utils.BEFORE, start_or_end=utils.END))
    else:
        assert action == KEY_EMERGENCY, f"Unexpected action value {action}"
        """
        Look for a meeting due to:
        - start before 30 (checkin_grace_min) minutes in the future
          (so the user could plausibly have got to this meeting)
        - end after 30 (checkin_grace_min) minutes in the past
          (so that the user might still be there)

        Some examples.
        If it is:
        - 12:34, then any meeting starting before 13:04 and ending after 12:04 would match
        - 13:17, then any meeting starting before 13:47 and ending after 12:47 would match

        A meeting from 14:00 to 15:00 would match if the current time is anything from 13:30 to 15:30

        This might conceivably match multiple meetings.
        """
        time_filters.append(utils.TimeFilter(minutes=ignore_after_min, before_or_after=utils.BEFORE, start_or_end=utils.START))
        time_filters.append(utils.TimeFilter(minutes=-ignore_after_min, before_or_after=utils.AFTER, start_or_end=utils.END))

    if end_before:
        # Explicit end before.
        logger.info("Explicit end before of %s", end_before)
        time_filters.append(utils.TimeFilter(datetime=end_before, before_or_after=utils.BEFORE, start_or_end=utils.END))

    filter = utils.build_time_filter(time_filters)

    # Retrieve the appointments
    appointments = manager.get_calendar_events(filter)

    # Filter out by address
    matching_appointments = []
    for appointment in appointments:
        for attendee in appointment['attendees']:
            address = attendee['emailAddress']['address'].lower()

            if address in addresses:
                logger.info("Match on address %s for meeting from %s to %s", address, appointment["start"], appointment["end"])
                matching_appointments.append(appointment)
                # No need to check any more attendees
                break
        else:
            logger.debug("Ignoring appointment %s as no address match", appointment['subject'])
            continue

    appointments = matching_appointments

    return appointments

def update_appointment(manager, appointment, action, ignore_already_done=False):
    """
    Update an appointment.

    Real errors are raised by exception (as they all imply graph API errors).

    Returns a flag "already_done" to indicate if the category was already present,
    in which case nothing is done.
    """
    # Note that we just use local time here - this is a human readable timestamp, not
    # used for any calculations.
    time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if action == KEY_CHECK_IN:
        logger.info("Update checkin for appointment subject %s", appointment['subject'])
        target_category = utils.CHECKED_IN
        body_message = f"<p>Checked in by phone at {time_now}</p>\r\n"
        message = "Your appointment has been checked in."
    elif action == KEY_CHECK_OUT:
        logger.info("Update checkout for appointment subject %s", appointment['subject'])
        target_category = utils.CHECKED_OUT
        body_message = f"<p>Checked out by phone at {time_now}</p>\r\n"
        message = "Your appointment has been checked out."
    else:
        logger.info("Update emergency for appointment subject %s", appointment['subject'])
        target_category = utils.EMERGENCY
        body_message = f"<p>Emergency reported by phone at {time_now}</p>\r\n"
        message = "Emergency call meeting found."

    # Set the category
    changes = {}
    categories = appointment['categories']
    if target_category in categories:
        logger.info('Appointment already has %s category', target_category)
        return True
    categories.append(target_category)
    changes['categories'] = categories

    body = appointment['body']
    body['content'] = body['content'].replace("</body>", f"{body_message}</body>")
    changes['body'] = body
    manager.patch_calendar_event(appointment['id'], changes)
    logger.info("Appointment updated successfully")

    return False

def process_appointments(manager, addresses, action):
    """
    Process Appointments

    This method finds relevant appointments and runs through them all, updating categories.

    It updates appointments as necessary, and returns a string indicating what happened and a
    boolean indicating if it was successful.
    """
    logger.info("Processing appointments list for action %s, addresses %s", action, addresses)

    # Assume error to start with, but set the default message for success.
    success = False
    if action == KEY_CHECK_IN:
        message = "Your appointment has been checked in."
    elif action == KEY_CHECK_OUT:
        message = "Your appointment has been checked out."
    else:
        # Caller should check these, but being defensive.
        assert action == KEY_EMERGENCY, f"Unexpected action value {action}"
        message = "Emergency appointment updated."

    appointments = get_calendar(manager, action, addresses)

    # We found the appointment to deal with. If there were multiple or none, we should deal with that.
    if len(appointments) == 0:
        logger.info("No appointments found for this user")
        if action == KEY_EMERGENCY:
            # This is considered a success for an emergency call, but we still drop out.
            success = True
        else:
            # Increment the counter for unfound appointments
            manager.increment_counter(METRIC_APPT_NOT_FOUND)
        return success, "No matching appointments found."
    if len(appointments) > 1:
        logger.info("More than one appointment found for this user - count: %d", len(appointments))
        if action == KEY_CHECK_IN:
            # If we cannot work out which meeting the user is trying to check into, there must be two overlapping
            # meetings; give up.
            logger.info("Multiple appointments found for checkin - count: %d", len(appointments))
            manager.increment_counter(METRIC_APPT_NOT_FOUND)
            return success, "Multiple matching appointments found."
        elif action == KEY_CHECK_OUT:
            # We allow this, so long as all but one has already been checked out. This is because we allow early checkouts,
            # and so our search can find the last meeting.
            logger.info("Multiple appointments found for checkout - count: %d", len(appointments))
            selected_appointments = []
            for appointment in appointments:
                if utils.CHECKED_OUT not in appointment['categories'] and utils.CHECKED_IN in appointment['categories']:
                    # This is a valid candidate for checkout, as it has been checked in but not checked out.
                    logger.info("Found a valid appointment candidate for checkout at %s (%s), subject: %s",
                                appointment['start']['dateTime'],
                                appointment['start']['timeZone'],
                                appointment['subject'])
                    selected_appointments.append(appointment)
                else:
                    logger.info("Ignoring appointment already checked out or not checked in at %s (%s), subject: %s",
                                appointment['start']['dateTime'],
                                appointment['start']['timeZone'],
                                appointment['subject'])

            appointments = selected_appointments
            if len(appointments) == 0:
                # No appointments left after filtering; everything is already checked out.
                logger.info("No valid appointments found for checkout")
                manager.increment_counter(METRIC_APPT_NOT_FOUND)
                return success, "No valid appointments found for checkout."
            if len(appointments) > 1:
                # Multiple appointments left after filtering. Something very wrong going on.
                logger.info("Multiple valid appointments found for checkout")
                manager.increment_counter(METRIC_APPT_NOT_FOUND)
                return success, "Multiple possible appointments were found for checkout."
        else:
            # For an emergency call, we just process all matching meetings.
           logger.info("Emergency call - process all meetings")

    # We are now down to a single meeting in the appointments list, unless this is an emergency.
    # Check if we are doing a checkin after checkout or a checkout without checkin
    for appointment in appointments:
        logger.debug("Deal with appointment at %s (%s), subject: %s",
                     appointment['start']['dateTime'],
                     appointment['start']['timeZone'],
                     appointment['subject'])
        # Note for the logic below that we already checked the array is of length 1 if checkin/out
        if action == KEY_CHECK_IN and utils.CHECKED_OUT in appointment['categories']:
            # Cannot check into an appointment to which you have checked out
            logger.info("Appointment checked out but trying to check in at %s (%s), subject: %s",
                         appointment['start']['dateTime'],
                         appointment['start']['timeZone'],
                         appointment['subject'])
            return success, "You are trying to check into a meeting that you have checked out of."
        if action == KEY_CHECK_OUT and utils.CHECKED_IN not in appointment['categories']:
            # Cannot check out of an appointment to which you have not checked in
            logger.info("Appointment not checked in but trying to check out at %s (%s), subject: %s",
                         appointment['start']['dateTime'],
                         appointment['start']['timeZone'],
                         appointment['subject'])
            return success, "You are trying to check out of a meeting that you have not checked into."

    already_done = False
    while appointments:
        appointment = appointments.pop()
        # Set the category
        already_done = update_appointment(manager, appointment, action)
        if already_done:
            logger.info("Appointment already marked with category at %s (%s), subject: %s",
                         appointment['start']['dateTime'],
                         appointment['start']['timeZone'],
                         appointment['subject'])
            if action == KEY_CHECK_IN:
                message = "Your appointment has already been checked in."
                manager.increment_counter(METRIC_DUPLICATE_CALL)
            elif action == KEY_CHECK_OUT:
                message = "Your appointment has already been checked out."
                manager.increment_counter(METRIC_DUPLICATE_CALL)
            else:
                message = "Emergency already registered."

    # If we got here, we consider it a success
    logger.info("Success!")
    success = True

    if action == KEY_CHECK_IN and not already_done:
        # We managed to check in - try to see if we missed a checkout
        logger.info("Checked in - look for missed checkout")
        start = appointment["start"]
        if start["timeZone"] != "Etc/GMT":
            # Somehow we have a non GMT timestamp, despite asking for GMT
            # Give up.
            logger.warn("Got a non-GMT timestamp, so giving up: %s", start)
            return success, message

        appointments = get_calendar(manager,
                                    KEY_CHECK_OUT,
                                    addresses,
                                    end_before=start["dateTime"])

        if len(appointments) != 1:
            # Multiple or no meetings, so do nothing. Maybe there was no missed checkout
            logger.info("Not got a single meeting, so no missed checkout - count %d", len(appointments))
            return success, message

        appointment = appointments.pop()
        logger.info("Possible missed checkout at %s (%s), subject: %s",
                    appointment['start']['dateTime'],
                    appointment['start']['timeZone'],
                    appointment['subject'])

        if utils.CHECKED_IN not in appointment['categories']:
            # Cannot check out of an appointment to which you have not checked in
            # Probably a missed checkin and checkout.
            logger.info("Appointment not checked in so no checkin at %s (%s), subject: %s",
                         appointment['start']['dateTime'],
                         appointment['start']['timeZone'],
                         appointment['subject'])
            return success, message

        already_done = update_appointment(manager, appointment, KEY_CHECK_OUT)
        if not already_done:
            # We update the message - terminating the sentence and adding the second batch
            logger.info("Found a missed checkout")
            message += " An earlier appointment has also been checked out."

    return success, message

def lambda_handler(event, context):
    """ Lambda Handler"""
    logger.info("Received call to handle")

    # Assume failure
    success = False
    resultMap = {}

    manager = utils.LoneWorkerManager("Connect", ALL_METRICS)

    action = event['Details']['Parameters']['buttonpressed']
    if action == KEY_CHECK_IN:
        logger.info("Check in")
        manager.increment_counter(METRIC_CHECKINS)
        resultMap["action"] = "Check in"
    elif action == KEY_CHECK_OUT:
        logger.info("Check out")
        manager.increment_counter(METRIC_CHECKOUTS)
        resultMap["action"] = "Check out"
    elif action == KEY_EMERGENCY:
        logger.info("Emergency")
        manager.increment_counter(METRIC_EMERGENCY)
        resultMap["action"] = "Emergency"
    else:
        logger.error("Invalid action selected")
        raise ValueError(f"Invalid action selected: {action}")

    try:
        phone_number = event['Details']['ContactData']['CustomerEndpoint']['Address']
    except KeyError as e:
        logger.error("Phone number not found")
        phone_number = None

    if phone_number:
        logger.info("Get values for phone number %s", phone_number)
        addresses, display_name = manager.phone_to_email(phone_number)
        # phone_found is used purely to give a better error message
        phone_found = True
    else:
        phone_number = "UNKNOWN"
        addresses = []
        displayName = "UNKNOWN"
        manager.increment_counter(METRIC_UNKNOWN_CALLER)
        phone_found = False

    resultMap["calling number"] = phone_number
    message = ""

    if action == KEY_CHECK_IN or action == KEY_CHECK_OUT:
        if addresses:
            logger.info("Check-in or out action selected")
            success, message = process_appointments(manager, addresses, action)
            if success:
                manager.increment_counter(METRIC_SUCCESS)
        else:
            logger.info("Giving up - no phone number or no matching addresses")
            if phone_found:
                message = "Unrecognised phone number."
            else:
                message = "Unable to find your phone number."
    else:
        logger.info("Emergency action selected")
        subject = "Emergency Assistance Required!"
        lines = []
        lines.append("Emergency call received")
        lines.append("")
        lines.append(f" Calling number      : {phone_number}")
        lines.append(f" Caller name if known: {display_name}")
        content = "\r\n".join(lines)
        manager.send_email("emergency", subject, content)
        message = "Emergency email sent." # This is not actually read out, so is just for diags purposes.

        if addresses:
            logger.info("Emergency mail sent - add emergency tag to meeting or meetings that may match")
            # We do not use the message we get back here except to log it; we do try to update the meeting, but cannot do more than that.
            _, unused_message = process_appointments(manager, addresses, action)
            logger.info("Got message from appointments: %s", unused_message)
            resultMap["appointment check result"] = unused_message

        # We consider having sent the email as a success, even if we could not find the meeting.
        success = True

    # Report back metrics
    manager.emit_metrics()

    resultMap["success"] = success
    if success:
        resultMap["message"] = message
    else:
        resultMap["message"] = f"An error occurred. {message} Please phone the office."

    logger.info("Returning structure: %s", resultMap)

    return resultMap