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


def _unknown_caller_call_count(mock_manager):
    """Count how many times increment_counter was called with METRIC_UNKNOWN_CALLER,
    since assert_any_call cannot distinguish one call from a double increment."""
    return sum(
        1 for call in mock_manager.increment_counter.call_args_list
        if call.args and call.args[0] == connect.METRIC_UNKNOWN_CALLER
    )


def _withheld_event(action, address="anonymous"):
    return {
        "Details": {
            "Parameters": {"buttonpressed": action},
            "ContactData": {"CustomerEndpoint": {"Address": address}}
        }
    }


def test_lambda_handler_withheld_checkin(mock_manager):
    """A withheld caller ID on check-in gets the withheld-specific message, makes
    no Graph lookup, and increments UnknownCaller exactly once."""
    event = _withheld_event(connect.KEY_CHECK_IN)

    result = connect.lambda_handler(event, None)

    assert not result["success"]
    assert result["message"] == (
        "An error occurred. Your caller ID was withheld, so we cannot identify you. Please phone the office."
    )
    assert result["calling number"] == "WITHHELD"
    mock_manager.phone_to_email.assert_not_called()
    assert _unknown_caller_call_count(mock_manager) == 1


def test_lambda_handler_withheld_checkout(mock_manager):
    """Same as check-in, for check-out."""
    event = _withheld_event(connect.KEY_CHECK_OUT)

    result = connect.lambda_handler(event, None)

    assert not result["success"]
    assert result["message"] == (
        "An error occurred. Your caller ID was withheld, so we cannot identify you. Please phone the office."
    )
    assert result["calling number"] == "WITHHELD"
    mock_manager.phone_to_email.assert_not_called()
    assert _unknown_caller_call_count(mock_manager) == 1


def test_lambda_handler_withheld_checkin_whitespace_and_case(mock_manager):
    """Detection is case-insensitive and tolerant of surrounding whitespace."""
    event = _withheld_event(connect.KEY_CHECK_IN, address="  ANONYMOUS  ")

    result = connect.lambda_handler(event, None)

    assert result["calling number"] == "WITHHELD"
    assert result["message"] == (
        "An error occurred. Your caller ID was withheld, so we cannot identify you. Please phone the office."
    )
    mock_manager.phone_to_email.assert_not_called()
    assert _unknown_caller_call_count(mock_manager) == 1


def test_lambda_handler_withheld_emergency(mock_manager):
    """A withheld caller ID on an emergency call still sends the email, recording
    the calling number as withheld and the caller name as UNKNOWN, and does not
    touch UnknownCaller at all."""
    event = _withheld_event(connect.KEY_EMERGENCY)

    result = connect.lambda_handler(event, None)

    assert result["success"]
    assert result["calling number"] == "WITHHELD"
    mock_manager.phone_to_email.assert_not_called()
    mock_manager.send_email.assert_called_once()
    _, _, content = mock_manager.send_email.call_args[0]
    assert " Calling number      : WITHHELD" in content
    assert " Caller name if known: UNKNOWN" in content
    assert "anonymous" not in content
    assert _unknown_caller_call_count(mock_manager) == 0


def test_lambda_handler_missing_phone_increments_unknown_caller_once(mock_manager):
    """No number present in the event at all must increment UnknownCaller exactly
    once, not twice as the pre-fix code did (once when the number was found
    absent, once again when check-in found no addresses).

    This supersedes the older test_lambda_handler_missing_phone, which built
    the same event but used assert_any_call and so could not tell one
    increment from two."""
    event = {
        "Details": {
            "Parameters": {"buttonpressed": connect.KEY_CHECK_IN},
            "ContactData": {"CustomerEndpoint": {}}  # No Address field
        }
    }

    result = connect.lambda_handler(event, None)

    assert not result["success"]
    assert "Phone number missing" in result["message"]
    assert _unknown_caller_call_count(mock_manager) == 1


def test_lambda_handler_missing_phone_emergency_no_nameerror(mock_manager):
    """An emergency call with no number at all must not raise NameError (the
    pre-fix code assigned `displayName` but read `display_name`), must still
    send the emergency email, and must record the caller name as UNKNOWN."""
    event = {
        "Details": {
            "Parameters": {"buttonpressed": connect.KEY_EMERGENCY},
            "ContactData": {"CustomerEndpoint": {}}  # No Address field
        }
    }

    result = connect.lambda_handler(event, None)

    assert result["success"]
    mock_manager.send_email.assert_called_once()
    _, _, content = mock_manager.send_email.call_args[0]
    assert " Caller name if known: UNKNOWN" in content
    assert _unknown_caller_call_count(mock_manager) == 0

def test_lambda_handler_emergency_sends_email_when_lookup_fails(mock_manager):
    """A directory failure must not cost us an emergency notification. The
    email goes out with the calling number and an unknown name, and only then
    is the error allowed to surface."""
    mock_manager.phone_to_email.side_effect = RuntimeError("Graph is down")
    event = {
        "Details": {
            "Parameters": {"buttonpressed": connect.KEY_EMERGENCY},
            "ContactData": {"CustomerEndpoint": {"Address": "+441234567890"}}
        }
    }

    with pytest.raises(RuntimeError):
        connect.lambda_handler(event, None)

    mock_manager.send_email.assert_called_once()
    _, _, content = mock_manager.send_email.call_args[0]
    assert " Calling number      : +441234567890" in content
    assert " Caller name if known: UNKNOWN" in content


def test_lambda_handler_checkin_lookup_failure_sends_no_email(mock_manager):
    """Only the emergency path has a notification worth rescuing. A check-in
    lookup failure just propagates."""
    mock_manager.phone_to_email.side_effect = RuntimeError("Graph is down")
    event = {
        "Details": {
            "Parameters": {"buttonpressed": connect.KEY_CHECK_IN},
            "ContactData": {"CustomerEndpoint": {"Address": "+441234567890"}}
        }
    }

    with pytest.raises(RuntimeError):
        connect.lambda_handler(event, None)

    mock_manager.send_email.assert_not_called()
