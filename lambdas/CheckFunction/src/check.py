import requests
from datetime import datetime, timedelta
import loneworker_utils as utils

logger = utils.get_logger()

def send_warning_mail(manager, checkin, appointment):
    """
    Send a warning message about a meeting for which either checkin or checkout was missed.
    """
    logger.info("Sending warning mail")
    if checkin:
        subject = "Missed check-in"
        lines = ["Check-in was missed for an appointment"]
    else:
        subject = "Missed check-out"
        lines = ["Check-out was missed for an appointment"]

    lines.append(f"  Subject: {appointment['subject']}")
    lines.append(f"  Start time: {appointment['start']}")
    lines.append(f"  End time: {appointment['end']}")
    lines.append(f"  Meeting details: {appointment['body']['content']}")
    content = "\r\n".join(lines)

    # TODO: make this email address configurable - it was "LoneWorkerNotifications@seescape.org.uk"
    manager.send_mail("nobody@example.com", subject, content)

def get_calendar_items(manager):
    """
    Get Calendar items from the MS Graph API

    This code reads all two sets of events from the calendar of the configured user and returns them in two arrays.

    The first array is to catch appointments for which checkin should have occurred. This is those with a
    start time at least 15 minutes in the past, and no more than 75 minutes in the past.

    The second array is to catch appointments for which checkout should have occurred. This is those with an
    end time that is at least 15 minutes in the past, and no more than 75 minutes in the past.

    In both cases, we are giving 15 minutes grace, and ignoring anything that is older than an hour.
    """
    logger.info("Get calendar events")
    # Checkin filter finds events that started in the past hour
    checkin_filter = utils.build_time_filter(75, -15, utils.START)

    # Checkout filter finds those that ended in the past hour
    end_filter = utils.build_time_filter(75, -15, utils.END)

    # Send the calendar request
    checkin_appointments = manager.get_calendar_events(checkin_filter)
    checkout_appointments = manager.get_calendar_events(checkout_filter)
    logging.info("Returning %d checkin and %d checkout appointments", len(checkin_appointments), len(checkout_appointments))
    return checkin_appointments, checkout_appointments

def process_appointments(manager, appointments, checkin):
    """
    Process the Appointments
    """
    if checkin:
        target_category = utils.CHECKED_IN
        missed_category = utils.MISSED_CHECK_IN
    else:
        target_category = utils.CHECKED_OUT
        missed_category = utils.MISSED_CHECK_OUT

    for appointment in appointments:
        categories = appointment['categories']
        if target_category in categories:
            # Either we are looking for checkin and there was one, or for checkouts and there was one.
            continue
        if missed_category in categories:
            # We already flagged this as a problem
            continue
        if not checkin and utils.MISSED_CHECK_IN in categories:
            # We should not flag a missed checkout if we flagged a missed checkin
            continue


        # If we got here, there is a problem
        subject = appointment['subject']
        logger.warn("Missed checkin or checkout for appointment: %s", subject)
        send_warning_email(manager, checkin, appointment)

        # We managed to send an email to warn people, so update the appointment
        categories.append(missed_category)
        changes = {
            'subject': missed_category + ": " + subject,
            'categories': categories
        }
        manager.patch_calendar_event(appointment['id'], changes)
        logger.info("Appointment updated successfully")

def lambda_handler(event, context):
    """ Lambda Handler"""
    manager = utils.LoneWorkerManager()

    # Read the relevant appointments from the calendar
    checkin_appointments, checkout_appointments = get_calendar_items(manager)

    # Process the appointments as required
    process_appointments(manager, checkin_appointments, checkin=True)
    process_appointments(manager, checkout_appointments, checkin=False)
