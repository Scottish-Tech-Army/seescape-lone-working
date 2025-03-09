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

import pytest
from check import send_warning_mail

class DummyManager:
    def __init__(self):
        self.sent_mail = None

    def send_mail(self, subject, content):
        self.sent_mail = [subject, content]

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
    lines.append("  Start time: 2023-01-01T10:00:00")
    lines.append("  End time: 2023-01-01T11:00:00")
    lines.append("")
    lines.append("Attendee list:")
    lines.append("  No attendees found")
    lines.append("")
    lines.append("Meeting description:")
    lines.append("Meeting details info.")
    expected_content = "\r\n".join(lines)
    assert manager.sent_mail[0] == expected_subject
    assert manager.sent_mail[1] == expected_content

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
    lines.append("  Start time: 2023-01-02T14:00:00")
    lines.append("  End time: 2023-01-02T15:00:00")
    lines.append("")
    lines.append("Attendee list:")
    lines.append("  billy@example.com")
    lines.append("  sue@example.com")
    lines.append("")
    lines.append("Meeting description:")
    lines.append("Checkout details info.")
    expected_content = "\r\n".join(lines)
    assert manager.sent_mail[0] == expected_subject
    assert manager.sent_mail[1] == expected_content
