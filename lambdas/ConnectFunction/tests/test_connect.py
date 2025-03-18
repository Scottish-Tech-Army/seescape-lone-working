import sys
import os
import types
import pytest
from datetime import datetime
from unittest.mock import MagicMock

# Add the local src directories to the include path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))
# Add the dependencies directory to sys.path to load the proper loneworker_utils module.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../dependencies/src"))
# Dummy out boto3 so that loneworker_utils loads without trying to use boto3.
dummy_boto3 = types.ModuleType("boto3")
sys.modules["boto3"] = dummy_boto3

import connect
import loneworker_utils as utils

@pytest.fixture
def dummy_manager():
    manager = MagicMock()
    manager.get_calendar_events = MagicMock(return_value=[])
    manager.patch_calendar_event = MagicMock()
    manager.send_mail = MagicMock()
    return manager

def make_appointment(appointment_id="1", subject="Test Appointment", categories=None, body_preview="", attendee_mails=[]):
    if categories is None:
        categories = []
    attendees = []
    for mail in attendee_mails:
        attendee = {'emailAddress': {'address' : mail}}
        attendees.append(attendee)

    return {
        "id": appointment_id,
        "subject": subject,
        "categories": categories,
        "attendees": attendees,
        "bodyPreview": body_preview,
        "body": {"content": "Details"}
    }

def test_process_appointments_check_in(dummy_manager):
    addresses = ["billy@example.com"]
    appointments = [
        make_appointment(categories=[], attendee_mails=addresses)
    ]
    result = connect.process_appointments(dummy_manager, appointments, addresses, connect.KEY_CHECK_IN)
    assert result == (True, "Your appointment has been checked in")
    dummy_manager.patch_calendar_event.assert_called_once()
    assert "Checked-In" in appointments[0]["categories"]

def test_process_appointments_check_out(dummy_manager):
    addresses = ["billy@example.com", "nomatch@example.com"]
    appointments = [
        make_appointment(categories=["Checked-In"], attendee_mails=addresses)
    ]
    addresses = ["billy@example.com", "jim@example.com"]
    result = connect.process_appointments(dummy_manager, appointments, addresses, connect.KEY_CHECK_OUT)
    assert result == (True, "Your appointment has been checked out")
    dummy_manager.patch_calendar_event.assert_called_once()
    assert "Checked-Out" in appointments[0]["categories"]

def test_process_appointments_no_matching_appointments(dummy_manager):
    addresses = ["billy@example.com"]
    appointments = [
        make_appointment(categories=[],  attendee_mails=addresses)
    ]
    addresses = ["fred@example.com"]
    result = connect.process_appointments(dummy_manager, appointments, addresses, connect.KEY_CHECK_IN)
    assert result == (False, "No matching appointments found.")
    assert not dummy_manager.patch_calendar_event.called

def test_process_appointments_multiple_matching_appointments(dummy_manager):
    appointments = [
        make_appointment(categories=[], attendee_mails=["jim@example.com", "BILLY@example.com"]),
        make_appointment(categories=[], attendee_mails=["billy@example.com"])
    ]
    addresses = ["billy@example.com"]
    result = connect.process_appointments(dummy_manager, appointments, addresses, connect.KEY_CHECK_IN)
    assert result == (False, "Multiple matching appointments found.")
    assert not dummy_manager.patch_calendar_event.called

def test_process_appointments_already_checked_in(dummy_manager):
    appointments = [
        make_appointment(categories=["Checked-In"], attendee_mails=["jim@example.com", "BILLY@example.com"]),
        make_appointment(categories=[], attendee_mails=["sue@example.com"])
    ]
    addresses = ["billy@example.com"]
    result = connect.process_appointments(dummy_manager, appointments, addresses, connect.KEY_CHECK_IN)
    assert result == (True, "Your appointment has already been checked in")
    dummy_manager.patch_calendar_event.assert_called_once()
    assert "Checked-In" in appointments[0]["categories"]

def test_process_appointments_already_checked_out(dummy_manager):
    addresses = ["billy@example.com"]
    appointments = [
        make_appointment(categories=["Checked-Out", "Checked-In"], attendee_mails=addresses)
    ]
    result = connect.process_appointments(dummy_manager, appointments, addresses, connect.KEY_CHECK_OUT)
    assert result == (True, "Your appointment has already been checked out")
    dummy_manager.patch_calendar_event.assert_called_once()
    assert "Checked-Out" in appointments[0]["categories"]

def test_process_appointments_check_out_no_checkin(dummy_manager):
    addresses = ["billy@example.com"]
    appointments = [
        make_appointment(categories=["Random stuff"], attendee_mails=addresses)
    ]
    result = connect.process_appointments(dummy_manager, appointments, addresses, connect.KEY_CHECK_OUT)
    assert result == (False, "No matching appointments found.")
    dummy_manager.patch_calendar_event.assert_not_called()

def test_process_appointments_invalid_action(dummy_manager):
    addresses = ["billy@example.com"]
    with pytest.raises(AssertionError):
        connect.process_appointments(dummy_manager, [], addresses, "invalid_action")
