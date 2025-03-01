import requests
from datetime import datetime
import os

import loneworker_utils as utils

KEY_CHECK_IN="1"
KEY_CHECK_OUT="2"
KEY_EMERGENCY="3"

logger = utils.get_logger()

def getCalendar(manager, action):
    """
    Get Calendar items from the MS Graph API

    This code reads relevant events from the calendar of the configured user and returns them in an array.
    """
    logger.info("Get calendar events - action %s", action)

    time_filters = []
    if action == KEY_CHECK_IN:
        # Look for a meeting due to start between 30 minutes ago and 30 minutes in the future.
        time_filters.append(utils.TimeFilter(minutes=-30, before_or_after=utils.AFTER, start_or_end=utils.START))
        time_filters.append(utils.TimeFilter(minutes=30, before_or_after=utils.BEFORE, start_or_end=utils.START))
    elif action == KEY_CHECK_IN:
        # Look for a meeting due to end between 30 minutes ago and 30 minutes in the future.
        time_filters.append(utils.TimeFilter(minutes=-30, before_or_after=utils.AFTER, start_or_end=utils.END))
        time_filters.append(utils.TimeFilter(minutes=30, before_or_after=utils.BEFORE, start_or_end=utils.END))
    else:
        # Look for a meeting due to start no later than 90 minutes ago, and to end no sooner than 15 minutes in the past
        assert action == KEY_EMERGENCY, "Unexpected action value"
        time_filters.append(utils.TimeFilter(minutes=-75, before_or_after=utils.AFTER, start_or_end=utils.START))
        time_filters.append(utils.TimeFilter(minutes=15, before_or_after=utils.BEFORE, start_or_end=utils.END))

    filter = utils.build_time_filter(time_filters)

    # Retrieve the appointments
    appointments = manager.get_calendar_events(filter)
    return appointments

def process_appointments(manager, appointments, staffid, action):
    """
    Process Appointments

    This method runs through all appointments found in the previous step.

    - It ignores all appointments that do not have "ID:staffid" in the body
    - If this is a checkin, then it changes the subject and categories of the appointment
    - If this is a checkout, it looks for a corresponding checked in appointment

    It updates appointments as necessary, and returns a string indicating what to do.
    """
    logger.info("Processing appointments list for ID %s, action %s", staffid, action)
    id_string = f"ID:{staffid}"

    # Caller should check this, but being defensive.
    assert action == KEY_CHECK_IN or action == KEY_CHECK_OUT or action == KEY_EMERGENCY, "Unexpected action value"

    # We first ditch any appointments that do not match the staff ID.
    matching_appointments = []
    for appointment in appointments:
        if not id_string in appointment['bodyPreview']:
            # Does not match the ID - ignore it.
            logger.debug("Ignoring appointment %s", appointment['subject'])
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
        return "No matching appointments found - please phone the office"
    if len(matching_appointments) > 1:
        return "Multiple matching appointments found - please phone the office"

    appointment = matching_appointments.pop()

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
        message = "" # This will be ignored

    # Set the category
    changes = {}
    categories = appointment['categories']
    if target_category in categories:
        logger.info('Appointment already has %s category', target_category)
        if action == KEY_CHECK_IN:
            message = "Your appointment has already been checked in"
        elif action == KEY_CHECK_OUT:
            message = "Your appointment has already been checked out"
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

    return message

def lambda_handler(event, context):
    """ Lambda Handler"""

    manager = utils.LoneWorkerManager()

    staff_id = event['Details']['ContactData']['Attributes']['idnumber']
    action = event['Details']['Parameters']['buttonpressed']

    headers = {
        'Authorization': 'Bearer ' + manager.token,
        'Content-Type': 'application/json',
        'Prefer': 'outlook.timezone="Europe/London"'
    }

    message = ""

    if action == KEY_CHECK_IN or action == KEY_CHECK_OUT:
        logger.info("Check-in or out action selected")
        appointments = getCalendar(manager, action)
        message = process_appointments(manager, appointments, staff_id, action)
    elif action == KEY_EMERGENCY:
        logger.info("Emergency action selected")
        # TODO: recipient was LoneWorkerNotifications@seescape.org.uk; make configurable
        subject = "Emergency Assistance Required!",
        content = "Emergency Assistance is required for ID " + staff_id
        manager.send_email("nobody@example.com", subject, content)
        message = "Message processed" # Deliberately vague, in case the SOS is overheard

        logger.info("Emergency mail sent - add emergency tag")
        appointments = getCalendar(manager, action)
        # We do not use the message we get back here except to log it; we do try to update the meeting, but cannot do more than that.
        unused_message = process_appointments(manager, appointments, staff_id, action)

        logger.info("Got message from appointments: %s", unused_message)
    else:
        logger.error("Invalid action selected")
        raise ValueError(f"Invalid action selected: {action}")

    resultMap = {
            "message" : message
            }

    return resultMap