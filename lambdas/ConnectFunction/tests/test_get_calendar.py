import sys
import os
import types
import pytest
from unittest.mock import MagicMock
from datetime import datetime

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
    manager.get_app_cfg = MagicMock(return_value={
        "checkin_grace_min": 15,
        "checkout_grace_min": 15,
        "ignore_after_min": 75
    })
    return manager


def _time_filters_passed_to(manager):
    """Return the list of TimeFilter objects passed to the most recent get_calendar_events call."""
    manager.get_calendar_events.assert_called_once()
    call = manager.get_calendar_events.mock_calls[0]
    return call.args[0]

def make_appointment(appointment_id="1", subject="Test Appointment", attendee_mails=[], start_time="2024-01-01T10:00:00", end_time="2024-01-01T11:00:00"):
    attendees = []
    for mail in attendee_mails:
        attendee = {'emailAddress': {'address': mail}}
        attendees.append(attendee)

    return {
        "id": appointment_id,
        "subject": subject,
        "attendees": attendees,
        "start": {"dateTime": start_time, "timeZone": "Etc/GMT"},
        "end": {"dateTime": end_time, "timeZone": "Etc/GMT"}
    }

def test_get_calendar_checkin_filters(dummy_manager):
    """Test that check-in action creates correct time filters"""
    connect.get_calendar(dummy_manager, connect.KEY_CHECK_IN, ["test@example.com"])

    time_filters = _time_filters_passed_to(dummy_manager)

    # Should have two time filters for check-in
    assert len(time_filters) == 2
    # First filter: after -15 minutes
    assert time_filters[0].minutes == -15
    assert time_filters[0].before_or_after == utils.AFTER
    assert time_filters[0].start_or_end == utils.START
    # Second filter: before +15 minutes
    assert time_filters[1].minutes == 15
    assert time_filters[1].before_or_after == utils.BEFORE
    assert time_filters[1].start_or_end == utils.START

def test_get_calendar_checkout_filters(dummy_manager):
    """Test that check-out action creates correct time filters"""
    connect.get_calendar(dummy_manager, connect.KEY_CHECK_OUT, ["test@example.com"])

    time_filters = _time_filters_passed_to(dummy_manager)

    # Should have two time filters for check-out
    assert len(time_filters) == 2
    # First filter: after -15 minutes from end
    assert time_filters[0].minutes == -15
    assert time_filters[0].before_or_after == utils.AFTER
    assert time_filters[0].start_or_end == utils.END
    # Second filter: before +75 minutes from end
    assert time_filters[1].minutes == 75
    assert time_filters[1].before_or_after == utils.BEFORE
    assert time_filters[1].start_or_end == utils.END

def test_get_calendar_emergency_filters(dummy_manager):
    """Test that emergency action creates correct time filters"""
    connect.get_calendar(dummy_manager, connect.KEY_EMERGENCY, ["test@example.com"])

    time_filters = _time_filters_passed_to(dummy_manager)

    # Should have two time filters for emergency
    assert len(time_filters) == 2
    # First filter: before +75 minutes from start
    assert time_filters[0].minutes == 75
    assert time_filters[0].before_or_after == utils.BEFORE
    assert time_filters[0].start_or_end == utils.START
    # Second filter: after -75 minutes from end
    assert time_filters[1].minutes == -75
    assert time_filters[1].before_or_after == utils.AFTER
    assert time_filters[1].start_or_end == utils.END

def test_get_calendar_end_before_filter(dummy_manager):
    """Test that end_before parameter adds correct filter"""
    end_before = "2024-01-01T12:00:00"
    connect.get_calendar(dummy_manager, connect.KEY_CHECK_IN, ["test@example.com"], end_before=end_before)

    time_filters = _time_filters_passed_to(dummy_manager)

    # Should have three filters (2 for check-in + 1 for end_before)
    assert len(time_filters) == 3
    # Last filter should be the end_before
    assert time_filters[2].datetime == end_before
    assert time_filters[2].before_or_after == utils.BEFORE
    assert time_filters[2].start_or_end == utils.END

def test_get_calendar_address_filtering(dummy_manager):
    """Test that appointments are filtered by attendee email addresses"""
    appointments = [
        make_appointment(appointment_id="1", attendee_mails=["match@example.com", "other@example.com"]),
        make_appointment(appointment_id="2", attendee_mails=["nomatch@example.com"]),
        make_appointment(appointment_id="3", attendee_mails=["MATCH@EXAMPLE.COM"]),  # Test case insensitive
        make_appointment(appointment_id="4", attendee_mails=[])  # Test no attendees
    ]
    dummy_manager.get_calendar_events.return_value = appointments

    result = connect.get_calendar(dummy_manager, connect.KEY_CHECK_IN, ["match@example.com"])

    # Should return appointments 1 and 3 (case insensitive match)
    assert len(result) == 2
    assert result[0]["id"] == "1"
    assert result[1]["id"] == "3"

def test_get_calendar_invalid_action(dummy_manager):
    """Test that invalid action raises assertion error"""
    with pytest.raises(AssertionError):
        connect.get_calendar(dummy_manager, "INVALID", ["test@example.com"])