import requests
from datetime import datetime, timedelta
import loneworker_utils as utils

METRIC_MEETINGS_CHECKED = "MeetingsChecked"
METRIC_CHECKINS_MISSED = "CheckinsMissed"
METRIC_CHECKOUTS_MISSED = "CheckoutsMissed"

ALL_METRICS = [METRIC_MEETINGS_CHECKED, METRIC_CHECKINS_MISSED, METRIC_CHECKOUTS_MISSED]

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
    lines.append(f"  Start time: {appointment['start']['dateTime']} (GMT)")
    lines.append(f"  End time: {appointment['end']['dateTime']} (GMT)")

    lines.append(f"")
    lines.append(f"Attendee list:")

    attendees = appointment['attendees']
    for attendee in attendees:
        address = attendee['emailAddress']['address'].lower()
        lines.append(f"  {address}")

    lines.append(f"")
    lines.append(f"Meeting description:")
    lines.append(f"{appointment['bodyPreview']}")
    content = "\r\n".join(lines)

    manager.send_mail(subject, content)

def get_calendar_items(manager):
    """
    Get Calendar items from the MS Graph API

    This code reads all two sets of events from the calendar of the configured user and returns them in two arrays.

    The first array is to catch appointments for which checkin should have occurred. This is those with a
    start time at least 15 minutes in the past, and no more than 75 minutes in the past.

    The second array is to catch appointments for which checkout should have occurred. This is those with an
    end time that is at least 15 minutes in the past, and no more than 75 minutes in the past.

    In both cases, we are giving 15 minutes grace, and ignoring anything that is older than 75 minutes.

    All of these numbers are configurable.
    - The parameter "15" is in "grace_min"
    - The parameter "75" is in "ignore_after_min"
    """
    logger.info("Get calendar events")

    app_cfg = manager.get_app_cfg()
    grace_min = app_cfg["grace_min"]
    ignore_after_min = app_cfg["ignore_after_min"]

    # Checkin filter finds events starting between 75 and 15 minutes ago
    checkin_filters = []
    checkin_filters.append(utils.TimeFilter(minutes=-ignore_after_min, before_or_after=utils.AFTER, start_or_end=utils.START))
    checkin_filters.append(utils.TimeFilter(minutes=-grace_min, before_or_after=utils.BEFORE, start_or_end=utils.START))
    checkin_filter_str = utils.build_time_filter(checkin_filters)

    # Checkout filter finds those that ended between 15 minutes ago, and 75 minutes ago - as above, but end time
    checkout_filters = []
    checkout_filters.append(utils.TimeFilter(minutes=-ignore_after_min, before_or_after=utils.AFTER, start_or_end=utils.END))
    checkout_filters.append(utils.TimeFilter(minutes=-grace_min, before_or_after=utils.BEFORE, start_or_end=utils.END))
    checkout_filter_str = utils.build_time_filter(checkout_filters)

    # Send the calendar request
    checkin_appointments = manager.get_calendar_events(checkin_filter_str)
    checkout_appointments = manager.get_calendar_events(checkout_filter_str)
    logger.info("Returning %d checkin and %d checkout appointments", len(checkin_appointments), len(checkout_appointments))
    return checkin_appointments, checkout_appointments

def process_appointments(manager, appointments, checkin):
    """
    Process the Appointments
    """
    if checkin:
        logger.info("Checking for missed checkin")
        target_category = utils.CHECKED_IN
        missed_category = utils.MISSED_CHECK_IN
        metric = METRIC_CHECKINS_MISSED
    else:
        logger.info("Checking for missed checkout")
        target_category = utils.CHECKED_OUT
        missed_category = utils.MISSED_CHECK_OUT
        metric = METRIC_CHECKOUTS_MISSED

    # Update metrics to report how many metrics we have checked.
    manager.increment_counter(METRIC_MEETINGS_CHECKED, len(appointments))

    for appointment in appointments:
        logger.info("Checking appointment at %s (%s), subject: %s",
                     appointment['start']['dateTime'],
                     appointment['start']['timeZone'],
                     appointment['subject'])
        categories = appointment['categories']
        if target_category in categories:
            # Either we are looking for checkin and there was one, or for checkouts and there was one.
            logger.debug("Already checked in / out - %s present already", target_category)
            continue
        if missed_category in categories:
            # We already flagged this as a problem
            logger.debug("Already marked - %s present already", missed_category)
            continue
        if not checkin and not utils.CHECKED_IN in categories:
            # We should not flag a missed checkout if we never checked in
            logger.debug("Ignoring missed checkout where no checkin either")
            continue
        if not appointment['attendees']:
            # No attendees for this appointment, so ignore it
            logger.debug("Ignoring meeting without attendees")
            continue

        # If we got here, there is a problem with this appointment
        subject = appointment['subject']
        logger.warn("Missed checkin or checkout for appointment: %s", subject)
        send_warning_mail(manager, checkin, appointment)

        # Update metrics for this event.
        manager.increment_counter(metric)

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
    manager = utils.LoneWorkerManager("Check", ALL_METRICS)

    # Read the relevant appointments from the calendar
    checkin_appointments, checkout_appointments = get_calendar_items(manager)

    # Process the appointments as required
    process_appointments(manager, checkin_appointments, checkin=True)
    process_appointments(manager, checkout_appointments, checkin=False)

    # Report back metrics
    manager.emit_metrics()

    resultMap = {
            "message" : "Routine check completed"
            }

    metrics = manager.get_metrics()

    resultMap["metrics"] = {}

    resultMap["metrics"]["Meetings checked"] = metrics[METRIC_MEETINGS_CHECKED]
    resultMap["metrics"]["Missed checkins reported"] = metrics[METRIC_CHECKINS_MISSED]
    resultMap["metrics"]["Missed checkouts reported"] = metrics[METRIC_CHECKOUTS_MISSED]

    logger.info("Returning structure: %s", resultMap)

    return resultMap
