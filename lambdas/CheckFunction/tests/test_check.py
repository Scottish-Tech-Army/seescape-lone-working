import sys
import os
import types

# Add the local src directories to the include path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))
# Add the dependencies directory to sys.path to load the proper loneworker_utils module.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../dependencies/src"))
# Dummy out boto3 so that loneworker_utils loads without trying to use boto3.
dummy_boto3 = types.ModuleType("boto3")
sys.modules["boto3"] = dummy_boto3

from datetime import date

import pytest
from check import send_warning_mail, days_to_expiry, INVALID_DAYS_TO_EXPIRY

class DummyManager:
    def __init__(self):
        self.sent_mail = None

    def send_email(self, type, subject, content):
        self.sent_mail = [type, subject, content]

def test_send_warning_mail_checkin():
    manager = DummyManager()
    appointment = {
        'subject': 'Test Meeting',
        'start': {'dateTime': '2023-01-01T10:00:00'},
        'end': {'dateTime': '2023-01-01T11:00:00'},
        'bodyPreview': 'Meeting details info.',
        'attendees': []
    }
    send_warning_mail(manager, True, appointment)
    assert manager.sent_mail is not None
    expected_subject = "Missed check-in"
    lines = []

    lines.append("Check-in was missed for an appointment")
    lines.append("  Subject: Test Meeting")
    lines.append("  Start time: 2023-01-01T10:00:00 (GMT)")
    lines.append("  End time: 2023-01-01T11:00:00 (GMT)")
    lines.append("")
    lines.append("Attendee list:")
    lines.append("")
    lines.append("Meeting description:")
    lines.append("Meeting details info.")
    expected_content = "\r\n".join(lines)
    assert manager.sent_mail[0] == "overdue"
    assert manager.sent_mail[1] == expected_subject
    assert manager.sent_mail[2] == expected_content


# ---- days_to_expiry ----

# Fixed reference date so tests are deterministic and survive the calendar.
TODAY = date(2026, 5, 6)

def test_days_to_expiry_future_date():
    # 30 days ahead → 30 days
    assert days_to_expiry("2026-06-05", today=TODAY) == 30

def test_days_to_expiry_today():
    assert days_to_expiry("2026-05-06", today=TODAY) == 0

def test_days_to_expiry_expired():
    # Already expired by 5 days — clamped to 0 so CloudWatch's Count unit
    # accepts the value. The < 7 alarm is already firing and the secret will
    # start failing, so other alarms cover the "actually expired" case.
    assert days_to_expiry("2026-05-01", today=TODAY) == 0

def test_days_to_expiry_far_future():
    # Far-future placeholder — well above the 366-day invalid threshold
    days = days_to_expiry("9999-12-31", today=TODAY)
    assert days > 366

def test_days_to_expiry_none():
    # Missing SSM parameter — surfaces as None
    assert days_to_expiry(None, today=TODAY) == INVALID_DAYS_TO_EXPIRY

def test_days_to_expiry_empty_string():
    assert days_to_expiry("", today=TODAY) == INVALID_DAYS_TO_EXPIRY

def test_days_to_expiry_garbage():
    assert days_to_expiry("not a date", today=TODAY) == INVALID_DAYS_TO_EXPIRY

def test_days_to_expiry_wrong_format():
    # Common mistake: UK format
    assert days_to_expiry("06/05/2026", today=TODAY) == INVALID_DAYS_TO_EXPIRY

def test_days_to_expiry_strips_whitespace():
    # Operators may paste with trailing whitespace; tolerate it
    assert days_to_expiry("  2026-06-05  ", today=TODAY) == 30


def test_send_warning_mail_checkout():
    manager = DummyManager()
    appointment = {
        'subject': 'Test Meeting 2',
        'start': {'dateTime': '2023-01-02T14:00:00'},
        'end': {'dateTime': '2023-01-02T15:00:00'},
        'bodyPreview': 'Checkout details info.',
        'attendees': [
            { 'emailAddress': {'address': 'billy@example.com'}},
            { 'emailAddress': {'address': 'Sue@example.com'}}
        ]
    }
    send_warning_mail(manager, False, appointment)
    assert manager.sent_mail is not None
    expected_subject = "Missed check-out"
    lines = []
    lines.append("Check-out was missed for an appointment")
    lines.append("  Subject: Test Meeting 2")
    lines.append("  Start time: 2023-01-02T14:00:00 (GMT)")
    lines.append("  End time: 2023-01-02T15:00:00 (GMT)")
    lines.append("")
    lines.append("Attendee list:")
    lines.append("  billy@example.com")
    lines.append("  sue@example.com")
    lines.append("")
    lines.append("Meeting description:")
    lines.append("Checkout details info.")
    expected_content = "\r\n".join(lines)
    assert manager.sent_mail[0] == "overdue"
    assert manager.sent_mail[1] == expected_subject
    assert manager.sent_mail[2] == expected_content
