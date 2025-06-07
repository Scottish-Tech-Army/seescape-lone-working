import sys
import os
import types
import pytest
from unittest.mock import MagicMock, patch

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
def mock_manager():
    with patch('loneworker_utils.LoneWorkerManager') as mock:
        manager = MagicMock()
        mock.return_value = manager
        manager.phone_to_email = MagicMock(return_value=(["test@example.com"], "Test User"))
        manager.get_calendar_events = MagicMock(return_value=[])
        manager.increment_counter = MagicMock()
        manager.emit_metrics = MagicMock()
        manager.get_app_cfg = MagicMock(return_value={
            "checkin_grace_min": 15,
            "checkout_grace_min": 15,
            "ignore_after_min": 75
        })
        yield manager

def test_lambda_handler_checkin(mock_manager):
    """Test lambda handler with check-in action"""
    event = {
        "Details": {
            "Parameters": {"buttonpressed": connect.KEY_CHECK_IN},
            "ContactData": {"CustomerEndpoint": {"Address": "+441234567890"}}
        }
    }

    result = connect.lambda_handler(event, None)

    assert result["action"] == "Check in"
    assert result["calling number"] == "+441234567890"
    mock_manager.increment_counter.assert_any_call(connect.METRIC_CHECKINS)
    mock_manager.emit_metrics.assert_called_once()

def test_lambda_handler_checkout(mock_manager):
    """Test lambda handler with check-out action"""
    event = {
        "Details": {
            "Parameters": {"buttonpressed": connect.KEY_CHECK_OUT},
            "ContactData": {"CustomerEndpoint": {"Address": "+441234567890"}}
        }
    }

    result = connect.lambda_handler(event, None)

    assert result["action"] == "Check out"
    assert result["calling number"] == "+441234567890"
    mock_manager.increment_counter.assert_any_call(connect.METRIC_CHECKOUTS)
    mock_manager.emit_metrics.assert_called_once()

def test_lambda_handler_emergency(mock_manager):
    """Test lambda handler with emergency action"""
    event = {
        "Details": {
            "Parameters": {"buttonpressed": connect.KEY_EMERGENCY},
            "ContactData": {"CustomerEndpoint": {"Address": "+441234567890"}}
        }
    }

    result = connect.lambda_handler(event, None)

    assert result["action"] == "Emergency"
    assert result["calling number"] == "+441234567890"
    mock_manager.increment_counter.assert_any_call(connect.METRIC_EMERGENCY)
    mock_manager.send_email.assert_called_once()  # Emergency email should be sent
    mock_manager.emit_metrics.assert_called_once()

def test_lambda_handler_unknown_phone(mock_manager):
    """Test lambda handler with unknown phone number"""
    mock_manager.phone_to_email.return_value = ([], "UNKNOWN")
    event = {
        "Details": {
            "Parameters": {"buttonpressed": connect.KEY_CHECK_IN},
            "ContactData": {"CustomerEndpoint": {"Address": "+441234567890"}}
        }
    }

    result = connect.lambda_handler(event, None)

    assert not result["success"]
    assert "Unrecognised phone number" in result["message"]
    mock_manager.increment_counter.assert_any_call(connect.METRIC_UNKNOWN_CALLER)
    mock_manager.emit_metrics.assert_called_once()

def test_lambda_handler_missing_phone(mock_manager):
    """Test lambda handler with missing phone number"""
    event = {
        "Details": {
            "Parameters": {"buttonpressed": connect.KEY_CHECK_IN},
            "ContactData": {"CustomerEndpoint": {}}  # No Address field
        }
    }

    result = connect.lambda_handler(event, None)

    assert not result["success"]
    assert "Unable to find your phone number" in result["message"]
    mock_manager.increment_counter.assert_any_call(connect.METRIC_UNKNOWN_CALLER)
    mock_manager.emit_metrics.assert_called_once()

def test_lambda_handler_invalid_action(mock_manager):
    """Test lambda handler with invalid action"""
    event = {
        "Details": {
            "Parameters": {"buttonpressed": "INVALID"},
            "ContactData": {"CustomerEndpoint": {"Address": "+441234567890"}}
        }
    }

    with pytest.raises(ValueError, match="Invalid action selected"):
        connect.lambda_handler(event, None)

def test_lambda_handler_malformed_event():
    """Test lambda handler with malformed event structure"""
    event = {}  # Missing required fields

    with pytest.raises(KeyError):
        connect.lambda_handler(event, None)