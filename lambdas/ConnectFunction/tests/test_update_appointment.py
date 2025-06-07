import sys
import os
import types
import pytest
from unittest.mock import MagicMock
from datetime import datetime
from freezegun import freeze_time

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
    manager.patch_calendar_event = MagicMock()
    return manager

def make_test_appointment(categories=None, body_content="<body>Test content</body>"):
    """Helper to create a test appointment with specified categories and body content"""
    if categories is None:
        categories = []
    return {
        "id": "test-id",
        "subject": "Test Appointment",
        "categories": categories.copy(),  # Copy to prevent modification of input
        "body": {"content": body_content}
    }

@freeze_time("2024-01-01 10:00:00")
def test_update_appointment_checkin(dummy_manager):
    """Test updating an appointment with check-in status"""
    appointment = make_test_appointment()

    result = connect.update_appointment(dummy_manager, appointment, connect.KEY_CHECK_IN)

    assert result is False  # Not already done
    assert utils.CHECKED_IN in appointment["categories"]
    assert "<p>Checked in by phone at 2024-01-01 10:00:00</p>" in appointment["body"]["content"]
    dummy_manager.patch_calendar_event.assert_called_once_with(
        "test-id",
        {
            "categories": [utils.CHECKED_IN],
            "body": {"content": "<body>Test content<p>Checked in by phone at 2024-01-01 10:00:00</p>\r\n</body>"}
        }
    )

@freeze_time("2024-01-01 10:00:00")
def test_update_appointment_checkout(dummy_manager):
    """Test updating an appointment with check-out status"""
    appointment = make_test_appointment()

    result = connect.update_appointment(dummy_manager, appointment, connect.KEY_CHECK_OUT)

    assert result is False  # Not already done
    assert utils.CHECKED_OUT in appointment["categories"]
    assert "<p>Checked out by phone at 2024-01-01 10:00:00</p>" in appointment["body"]["content"]
    dummy_manager.patch_calendar_event.assert_called_once_with(
        "test-id",
        {
            "categories": [utils.CHECKED_OUT],
            "body": {"content": "<body>Test content<p>Checked out by phone at 2024-01-01 10:00:00</p>\r\n</body>"}
        }
    )

@freeze_time("2024-01-01 10:00:00")
def test_update_appointment_emergency(dummy_manager):
    """Test updating an appointment with emergency status"""
    appointment = make_test_appointment()

    result = connect.update_appointment(dummy_manager, appointment, connect.KEY_EMERGENCY)

    assert result is False  # Not already done
    assert utils.EMERGENCY in appointment["categories"]
    assert "<p>Emergency reported by phone at 2024-01-01 10:00:00</p>" in appointment["body"]["content"]
    dummy_manager.patch_calendar_event.assert_called_once_with(
        "test-id",
        {
            "categories": [utils.EMERGENCY],
            "body": {"content": "<body>Test content<p>Emergency reported by phone at 2024-01-01 10:00:00</p>\r\n</body>"}
        }
    )

def test_update_appointment_already_done(dummy_manager):
    """Test updating an appointment that already has the target category"""
    appointment = make_test_appointment(categories=[utils.CHECKED_IN])

    result = connect.update_appointment(dummy_manager, appointment, connect.KEY_CHECK_IN)

    assert result is True  # Already done
    dummy_manager.patch_calendar_event.assert_not_called()

def test_update_appointment_preserves_categories(dummy_manager):
    """Test that existing categories are preserved when updating"""
    appointment = make_test_appointment(categories=["ExistingCategory"])

    connect.update_appointment(dummy_manager, appointment, connect.KEY_CHECK_IN)

    assert "ExistingCategory" in appointment["categories"]
    assert utils.CHECKED_IN in appointment["categories"]
    assert len(appointment["categories"]) == 2
