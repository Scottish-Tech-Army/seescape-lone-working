import sys
import os
import types
import pytest
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

@pytest.fixture(autouse=True)
def patch_build_time_filter(monkeypatch):
    monkeypatch.setattr(utils, "build_time_filter", lambda time_filters: "dummy-filter")

@pytest.fixture
def dummy_manager():
    manager = MagicMock()
    manager.get_calendar_events = MagicMock(return_value=[])
    manager.patch_calendar_event = MagicMock()
    manager.send_email = MagicMock()
    return manager

def make_appointment(appointment_id="1", subject="Test Appointment", categories=None, body_preview="", attendee_mails=[], starttime="starttime"):
    if categories is None:
        categories = []
    attendees = []
    for mail in attendee_mails:
        attendee = {'emailAddress': {'address': mail}}
        attendees.append(attendee)

    return {
        "id": appointment_id,
        "subject": subject,
        "categories": categories,
        "attendees": attendees,
        "bodyPreview": body_preview,
        "body": {"content": "Details"},
        "start": {"dateTime": starttime,
                  "timeZone": "Etc/GMT"},
        "end": {"dateTime": "endtime",
                "timeZone": "Etc/GMT"},
    }

class TestProcessAppointmentsCheckin:
    """Tests for check-in functionality in process_appointments"""

    def test_successful_checkin(self, dummy_manager):
        """Test successful check-in to an appointment"""
        addresses = ["billy@example.com"]
        appointments = [
            make_appointment(categories=[], attendee_mails=addresses)
        ]
        dummy_manager.get_calendar_events.side_effect = [appointments, []]
        result = connect.process_appointments(dummy_manager, addresses, connect.KEY_CHECK_IN)
        assert result == (True, "Your appointment has been checked in.")

    def test_checkin_with_missed_checkout(self, dummy_manager, monkeypatch):
        """Test check-in that also finds and processes a missed check-out"""
        addresses = ["billy@example.com"]
        appointments = [
            make_appointment(categories=[], attendee_mails=addresses)
        ]
        second_appointments = [
            make_appointment(categories=["Checked-In"], attendee_mails=addresses)
        ]
        monkeypatch.setattr(dummy_manager, "get_calendar_events", MagicMock(side_effect=[appointments, second_appointments]))
        result = connect.process_appointments(dummy_manager, addresses, connect.KEY_CHECK_IN)
        assert result == (True, "Your appointment has been checked in. An earlier appointment has also been checked out.")

    def test_already_checked_in(self, dummy_manager):
        """Test attempting to check in to an already checked-in appointment"""
        addresses = ["billy@example.com"]
        appointments = [
            make_appointment(categories=["Checked-In"], attendee_mails=["jim@example.com", "BILLY@example.com"])
        ]
        dummy_manager.get_calendar_events.return_value = appointments
        result = connect.process_appointments(dummy_manager, addresses, connect.KEY_CHECK_IN)
        assert result == (True, "Your appointment has already been checked in.")

    def test_multiple_appointments_checkin(self, dummy_manager):
        """Test attempting to check in when multiple appointments are found"""
        addresses = ["billy@example.com"]
        appointments = [
            make_appointment(categories=[], attendee_mails=["billy@example.com"], starttime="meeting1"),
            make_appointment(categories=[], attendee_mails=["billy@example.com"], starttime="meeting2")
        ]
        dummy_manager.get_calendar_events.return_value = appointments
        result = connect.process_appointments(dummy_manager, addresses, connect.KEY_CHECK_IN)
        assert result == (False, "Multiple matching appointments found.")
        dummy_manager.increment_counter.assert_any_call(connect.METRIC_APPT_NOT_FOUND)

class TestProcessAppointmentsCheckout:
    """Tests for check-out functionality in process_appointments"""

    def test_successful_checkout(self, dummy_manager):
        """Test successful check-out from an appointment"""
        addresses = ["billy@example.com", "jim@example.com"]
        appointments = [
            make_appointment(categories=["Checked-In"], attendee_mails=["billy@example.com", "nomatch@example.com"])
        ]
        dummy_manager.get_calendar_events.return_value = appointments
        result = connect.process_appointments(dummy_manager, addresses, connect.KEY_CHECK_OUT)
        assert result == (True, "Your appointment has been checked out.")

    def test_checkout_without_checkin(self, dummy_manager):
        """Test attempting to check out without having checked in"""
        addresses = ["billy@example.com"]
        appointments = [
            make_appointment(categories=["Random stuff"], attendee_mails=addresses)
        ]
        dummy_manager.get_calendar_events.return_value = appointments
        result = connect.process_appointments(dummy_manager, addresses, connect.KEY_CHECK_OUT)
        assert result == (False, "You are trying to check out of a meeting that you have not checked into.")
        dummy_manager.patch_calendar_event.assert_not_called()

    def test_already_checked_out(self, dummy_manager):
        """Test attempting to check out from an already checked-out appointment"""
        addresses = ["billy@example.com"]
        appointments = [
            make_appointment(categories=["Checked-In", "Checked-Out"], attendee_mails=["jim@example.com", "BILLY@example.com"])
        ]
        dummy_manager.get_calendar_events.return_value = appointments
        result = connect.process_appointments(dummy_manager, addresses, connect.KEY_CHECK_OUT)
        assert result == (True, "Your appointment has already been checked out.")

    def test_early_checkout_single_valid(self, dummy_manager):
        """Test early check-out with one valid appointment among multiple"""
        addresses = ["billy@example.com"]
        appointments = [
            make_appointment(categories=["Checked-In", "Checked-Out"], attendee_mails=["jim@example.com", "BILLY@example.com"]),
            make_appointment(categories=["Checked-In"], attendee_mails=["billy@example.com"])
        ]
        dummy_manager.get_calendar_events.return_value = appointments
        result = connect.process_appointments(dummy_manager, addresses, connect.KEY_CHECK_OUT)
        assert result == (True, "Your appointment has been checked out.")

    def test_early_checkout_no_valid_appointments(self, dummy_manager):
        """Test early check-out with no valid appointments found"""
        addresses = ["billy@example.com"]
        appointments = [
            make_appointment(categories=["Checked-In", "Checked-Out"], attendee_mails=["billy@example.com"]),
            make_appointment(categories=[], attendee_mails=["billy@example.com"])
        ]
        dummy_manager.get_calendar_events.return_value = appointments
        result = connect.process_appointments(dummy_manager, addresses, connect.KEY_CHECK_OUT)
        assert result == (False, "No valid appointments found for checkout.")

class TestProcessAppointmentsEmergency:
    """Tests for emergency functionality in process_appointments"""

    def test_emergency_no_appointments(self, dummy_manager):
        """Test emergency call with no matching appointments"""
        addresses = ["billy@example.com"]
        dummy_manager.get_calendar_events.return_value = []
        result = connect.process_appointments(dummy_manager, addresses, connect.KEY_EMERGENCY)
        assert result == (True, "No matching appointments found.")  # Emergency is always considered successful

    def test_emergency_with_appointments(self, dummy_manager):
        """Test emergency call with matching appointments"""
        addresses = ["billy@example.com"]
        appointments = [
            make_appointment(categories=[], attendee_mails=addresses)
        ]
        dummy_manager.get_calendar_events.return_value = appointments
        result = connect.process_appointments(dummy_manager, addresses, connect.KEY_EMERGENCY)
        assert result == (True, "Emergency appointment updated.")

class TestProcessAppointmentsGeneral:
    """General tests for process_appointments"""

    def test_no_matching_appointments(self, dummy_manager):
        """Test when no matching appointments are found"""
        addresses = ["fred@example.com"]
        appointments = [
            make_appointment(categories=[], attendee_mails=["billy@example.com"])
        ]
        dummy_manager.get_calendar_events.return_value = appointments
        result = connect.process_appointments(dummy_manager, addresses, connect.KEY_CHECK_IN)
        assert result == (False, "No matching appointments found.")
        dummy_manager.increment_counter.assert_any_call(connect.METRIC_APPT_NOT_FOUND)

    def test_invalid_action(self, dummy_manager):
        """Test with invalid action"""
        addresses = ["billy@example.com"]
        with pytest.raises(AssertionError):
            connect.process_appointments(dummy_manager, addresses, "invalid_action")