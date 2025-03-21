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

def get_calendar(manager, action):
    """
    Get Calendar items from the MS Graph API

    This code reads relevant events from the calendar of the configured user and returns them in an array.
    """
    logger.info("Get calendar events - action %s", action)
    app_cfg = manager.get_app_cfg()

    checkin_grace_min = app_cfg["checkin_grace_min"]
    checkout_grace_min = app_cfg["checkout_grace_min"]
    ignore_after_min = app_cfg["ignore_after_min"]

    time_filters = []
    if action == KEY_CHECK_IN:
        # Look for a meeting due to start between 30 minutes ago and 30 minutes in the future (actually checkin_grace_min)
        time_filters.append(utils.TimeFilter(minutes=-checkin_grace_min, before_or_after=utils.AFTER, start_or_end=utils.START))
        time_filters.append(utils.TimeFilter(minutes=checkin_grace_min, before_or_after=utils.BEFORE, start_or_end=utils.START))
    elif action == KEY_CHECK_OUT:
        # Look for a meeting due to end between 30 minutes ago and 30 minutes in the future (actually checkout_grace_min)
        time_filters.append(utils.TimeFilter(minutes=-checkout_grace_min, before_or_after=utils.AFTER, start_or_end=utils.END))
        time_filters.append(utils.TimeFilter(minutes=checkout_grace_min, before_or_after=utils.BEFORE, start_or_end=utils.END))
    else:
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
        assert action == KEY_EMERGENCY, "Unexpected action value"
        time_filters.append(utils.TimeFilter(minutes=ignore_after_min, before_or_after=utils.BEFORE, start_or_end=utils.START))
        time_filters.append(utils.TimeFilter(minutes=-ignore_after_min, before_or_after=utils.AFTER, start_or_end=utils.END))

    filter = utils.build_time_filter(time_filters)

    # Retrieve the appointments
    appointments = manager.get_calendar_events(filter)
    return appointments

def process_appointments(manager, appointments, addresses, action):
    """
    Process Appointments

    This method runs through all appointments found in the previous step.

    - It ignores all appointments that do not have "ID:staffid" in the body
    - If this is a checkin, then it changes the subject and categories of the appointment
    - If this is a checkout, it looks for a corresponding checked in appointment

    It updates appointments as necessary, and returns a string indicating what to do.
    """
    logger.info("Processing appointments list for action %s, addresses %s", action, addresses)

    # Caller should check this, but being defensive.
    assert action == KEY_CHECK_IN or action == KEY_CHECK_OUT or action == KEY_EMERGENCY, "Unexpected action value"

    # Assume error to start with
    success = False

    # We first ditch any appointments that do not match the staff ID.
    matching_appointments = []
    for appointment in appointments:
        match = False
        for attendee in appointment['attendees']:
            address = attendee['emailAddress']['address'].lower()

            if address in addresses:
                logger.info("Match on address %s", address)
                match = True
                # No need to check any more attendees
                continue

        if not match:
            logger.debug("Ignoring appointment %s as no address match", appointment['subject'])
            continue

        if action == KEY_CHECK_IN and utils.CHECKED_OUT in appointment['categories']:
            # Cannot check into an appointment to which you have checked out
            logger.info("Appointment checked out - try the next one: %s", appointment['subject'])
            continue
        if action == KEY_CHECK_OUT and utils.CHECKED_IN not in appointment['categories']:
            # Cannot check out of an appointment to which you have not checked in
            logger.info("Appointment not checked in - try the next one: %s", appointment['subject'])
            continue
        matching_appointments.append(appointment)

    # We found the appointment to deal with. If there were multiple, we should give up now.
    # For an emergency, these are not important; nothing to do, and the message will be suppressed.
    if len(matching_appointments) == 0:
        logger.info("No appointments found for this user")
        if action != KEY_EMERGENCY:
            manager.increment_counter(METRIC_APPT_NOT_FOUND)
        else:
            # This is considered a success for an emergency call
            success = True
        return success, "No matching appointments found."
    if len(matching_appointments) > 1:
        logger.info("More than one appointment found for this user - count: %d", len(matching_appointments))
        if action != KEY_EMERGENCY:
            manager.increment_counter(METRIC_APPT_NOT_FOUND)
            return success, "Multiple matching appointments found."
        else:
            # For an emergency call, we just process all matching meetings.
           logger.info("Emergency call - process all meetings")

    time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if action == KEY_CHECK_IN:
        target_category = utils.CHECKED_IN
        body_message = f"<p>Checked in by phone at {time_now}</p>\r\n"
        message = "Your appointment has been checked in"
    elif action == KEY_CHECK_OUT:
        target_category = utils.CHECKED_OUT
        body_message = f"<p>Checked out by phone at {time_now}</p>\r\n"
        message = "Your appointment has been checked out"
    else:
        target_category = utils.EMERGENCY
        body_message = f"<p>Emergency reported by phone at {time_now}</p>\r\n"
        message = "Emergency call meeting found"

    while matching_appointments:
        appointment = matching_appointments.pop()
        # Set the category
        changes = {}
        categories = appointment['categories']
        if target_category in categories:
            logger.info('Appointment already has %s category', target_category)
            if action == KEY_CHECK_IN:
                message = "Your appointment has already been checked in"
                manager.increment_counter(METRIC_DUPLICATE_CALL)
            elif action == KEY_CHECK_OUT:
                message = "Your appointment has already been checked out"
                manager.increment_counter(METRIC_DUPLICATE_CALL)
            else:
                message = "Emergency already registered"
        else:
            logger.info("Update categories")
            categories.append(target_category)
            changes['categories'] = categories

        body = appointment['body']
        body['content'] = body['content'].replace("</body>", f"{body_message}</body>")
        changes['body'] = body
        manager.patch_calendar_event(appointment['id'], changes)
        logger.info("Appointment updated successfully")

    # If we got here, we consider it a success
    success = True
    return success, message

def lambda_handler(event, context):
    """ Lambda Handler"""
    logger.info("Received call to handle")
    manager = utils.LoneWorkerManager("Connect", ALL_METRICS)
    resultMap = {}

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

    # Assume failure
    success = False

    if action == KEY_CHECK_IN or action == KEY_CHECK_OUT:
        if addresses:
            logger.info("Check-in or out action selected")
            appointments = get_calendar(manager, action)
            success, message = process_appointments(manager, appointments, addresses, action)
            if success:
                manager.increment_counter(METRIC_SUCCESS)
        else:
            logger.info("Giving up - no phone number or no matching addresses")
            if phone_found:
                message = "Unable to find meeting matching your phone number"
            else:
                message = "Unable to find your phone number"
    else:
        logger.info("Emergency action selected")
        subject = "Emergency Assistance Required!"
        lines = []
        lines.append("Emergency call received")
        lines.append("")
        lines.append(f" Calling number      : {phone_number}")
        lines.append(f" Caller name if known: {display_name}")
        content = "\r\n".join(lines)
        manager.send_mail(subject, content)
        message = "Emergency email sent" # This is not actually read out, so is just for diags purposes.

        if addresses:
            logger.info("Emergency mail sent - add emergency tag to meeting or meetings that may match")
            appointments = get_calendar(manager, action)
            # We do not use the message we get back here except to log it; we do try to update the meeting, but cannot do more than that.
            success, unused_message = process_appointments(manager, appointments, addresses, action)
            logger.info("Got message from appointments: %s", unused_message)
            resultMap["appointment check result"] = unused_message

    # Report back metrics
    manager.emit_metrics()

    if success:
        resultMap["message"] = message
    else:
        resultMap["message"] = f"An error occurred. {message} Please phone the office."

    return resultMap