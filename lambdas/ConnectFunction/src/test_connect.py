import sys
import os
import types
import pytest
from datetime import datetime
from unittest.mock import MagicMock

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
    manager.send_email = MagicMock()
    return manager

def make_appointment(appointment_id="1", subject="Test Appointment", categories=None, body_preview=""):
    if categories is None:
        categories = []
    return {
        "id": appointment_id,
        "subject": subject,
        "categories": categories,
        "bodyPreview": body_preview,
        "body": {"content": "Details"}
    }

def test_process_appointments_check_in(dummy_manager):
    appointments = [
        make_appointment(categories=[], body_preview="ID:123")
    ]
    result = connect.process_appointments(dummy_manager, appointments, "123", connect.KEY_CHECK_IN)
    assert result == "Your appointment has been checked in"
    dummy_manager.patch_calendar_event.assert_called_once()
    assert "Checked-In" in appointments[0]["categories"]

def test_process_appointments_check_out(dummy_manager):
    appointments = [
        make_appointment(categories=["Checked-In"], body_preview="ID:123")
    ]
    result = connect.process_appointments(dummy_manager, appointments, "123", connect.KEY_CHECK_OUT)
    assert result == "Your appointment has been checked out"
    dummy_manager.patch_calendar_event.assert_called_once()
    assert "Checked-Out" in appointments[0]["categories"]

def test_process_appointments_no_matching_appointments(dummy_manager):
    appointments = [
        make_appointment(categories=[], body_preview="ID:456")
    ]
    result = connect.process_appointments(dummy_manager, appointments, "123", connect.KEY_CHECK_IN)
    assert result == "No matching appointments found - please phone the office"
    assert not dummy_manager.patch_calendar_event.called

def test_process_appointments_multiple_matching_appointments(dummy_manager):
    appointments = [
        make_appointment(categories=[], body_preview="ID:123"),
        make_appointment(categories=[], body_preview="ID:123")
    ]
    result = connect.process_appointments(dummy_manager, appointments, "123", connect.KEY_CHECK_IN)
    assert result == "Multiple matching appointments found - please phone the office"
    assert not dummy_manager.patch_calendar_event.called

def test_process_appointments_already_checked_in(dummy_manager):
    appointments = [
        make_appointment(categories=["Checked-In"], body_preview="ID:123"),
        make_appointment(categories=[], body_preview="ID:456")
    ]
    result = connect.process_appointments(dummy_manager, appointments, "123", connect.KEY_CHECK_IN)
    assert result == "Your appointment has already been checked in"
    dummy_manager.patch_calendar_event.assert_called_once()
    assert "Checked-In" in appointments[0]["categories"]

def test_process_appointments_already_checked_out(dummy_manager):
    appointments = [
        make_appointment(categories=["Checked-Out", "Checked-In"], body_preview="ID:123")
    ]
    result = connect.process_appointments(dummy_manager, appointments, "123", connect.KEY_CHECK_OUT)
    assert result == "Your appointment has already been checked out"
    dummy_manager.patch_calendar_event.assert_called_once()
    assert "Checked-Out" in appointments[0]["categories"]

def test_process_appointments_check_out_no_checkin(dummy_manager):
    appointments = [
        make_appointment(categories=["Random stuff"], body_preview="ID:456")
    ]
    result = connect.process_appointments(dummy_manager, appointments, "123", connect.KEY_CHECK_OUT)
    assert result == "No matching appointments found - please phone the office"
    dummy_manager.patch_calendar_event.assert_not_called()

def test_process_appointments_invalid_action(dummy_manager):
    with pytest.raises(AssertionError):
        connect.process_appointments(dummy_manager, [], "123", "invalid_action")
