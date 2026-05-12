import datetime as dt
import logging
import os
import sys
import types
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add the local src directories to the include path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))
# Dummy out boto3 so that loneworker_utils loads without trying to use boto3.
dummy_boto3 = types.ModuleType("boto3")
sys.modules["boto3"] = dummy_boto3

import loneworker_utils


def _event(start_offset_min, end_offset_min, now):
    """Build a minimal event dict whose start/end are the given minute offsets from now."""
    start_dt = now + timedelta(minutes=start_offset_min)
    end_dt = now + timedelta(minutes=end_offset_min)
    fmt = lambda d: d.strftime("%Y-%m-%dT%H:%M:%S.0000000")
    return {
        "start": {"dateTime": fmt(start_dt), "timeZone": "Etc/GMT"},
        "end": {"dateTime": fmt(end_dt), "timeZone": "Etc/GMT"},
    }


class TestLoneworkerUtils(unittest.TestCase):
    def test_get_logger(self):
        logger = loneworker_utils.get_logger()
        self.assertIsInstance(logger, logging.Logger)
        self.assertTrue(callable(logger.info))

    def test_parse_graph_datetime_strips_subsecond(self):
        parsed = loneworker_utils.parse_graph_datetime("2026-05-10T14:00:00.0000000")
        self.assertEqual(parsed, datetime(2026, 5, 10, 14, 0, 0, tzinfo=dt.timezone.utc))

    def test_parse_graph_datetime_handles_z_suffix(self):
        parsed = loneworker_utils.parse_graph_datetime("2026-05-10T14:00:00Z")
        self.assertEqual(parsed, datetime(2026, 5, 10, 14, 0, 0, tzinfo=dt.timezone.utc))

    def test_event_matches_start_window(self):
        now = datetime.now(dt.timezone.utc)
        time_filters = [
            loneworker_utils.TimeFilter(minutes=-10, before_or_after="after", start_or_end="start"),
            loneworker_utils.TimeFilter(minutes=10, before_or_after="before", start_or_end="start"),
        ]
        # Start at -5min: inside window.
        self.assertTrue(loneworker_utils.event_matches_time_filters(
            _event(-5, 55, now), time_filters, now))
        # Start at -20min: before window.
        self.assertFalse(loneworker_utils.event_matches_time_filters(
            _event(-20, 40, now), time_filters, now))
        # Start at +20min: after window.
        self.assertFalse(loneworker_utils.event_matches_time_filters(
            _event(20, 80, now), time_filters, now))

    def test_event_matches_end_window(self):
        now = datetime.now(dt.timezone.utc)
        time_filters = [
            loneworker_utils.TimeFilter(minutes=-75, before_or_after="after", start_or_end="end"),
            loneworker_utils.TimeFilter(minutes=-15, before_or_after="before", start_or_end="end"),
        ]
        # End at -30min: inside window.
        self.assertTrue(loneworker_utils.event_matches_time_filters(
            _event(-90, -30, now), time_filters, now))
        # End at -10min: too recent.
        self.assertFalse(loneworker_utils.event_matches_time_filters(
            _event(-70, -10, now), time_filters, now))

    def test_event_matches_explicit_datetime(self):
        now = datetime.now(dt.timezone.utc)
        cutoff = now - timedelta(minutes=30)
        cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%S.0000000")
        time_filters = [
            loneworker_utils.TimeFilter(datetime=cutoff_str, before_or_after="before", start_or_end="end"),
        ]
        # End before cutoff: matches.
        self.assertTrue(loneworker_utils.event_matches_time_filters(
            _event(-90, -45, now), time_filters, now))
        # End after cutoff: rejected.
        self.assertFalse(loneworker_utils.event_matches_time_filters(
            _event(-90, -15, now), time_filters, now))

    def test_event_matches_invalid(self):
        now = datetime.now(dt.timezone.utc)
        with self.assertRaises(ValueError):
            loneworker_utils.event_matches_time_filters(
                _event(-5, 55, now),
                [loneworker_utils.TimeFilter(minutes=10, before_or_after="after", start_or_end="invalid")],
                now)
        with self.assertRaises(ValueError):
            loneworker_utils.event_matches_time_filters(
                _event(-5, 55, now),
                [loneworker_utils.TimeFilter(minutes=10, before_or_after="invalid", start_or_end="start")],
                now)


def _make_manager(ignore_after_min=75):
    """Build a LoneWorkerManager with only the attributes get_calendar_events needs.

    Skipping __init__ avoids the AWS SSM and Graph token round-trips that
    construction normally performs.
    """
    mgr = loneworker_utils.LoneWorkerManager.__new__(loneworker_utils.LoneWorkerManager)
    mgr.calendar_view_url = "https://graph.microsoft.com/v1.0/users/x/calendar/calendarView"
    mgr.headers = {"Authorization": "Bearer test"}
    mgr.cfg = MagicMock()
    mgr.cfg.get_app_cfg.return_value = {"ignore_after_min": ignore_after_min}
    mgr.app_type = "Connect"
    return mgr


def _ok_response(value, next_link=None):
    """Build a fake requests.Response stand-in with the given JSON body."""
    body = {"value": value}
    if next_link is not None:
        body["@odata.nextLink"] = next_link
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = body
    return response


def _event_at(event_id, start_dt, end_dt):
    """Build a /calendarView-shaped event with the given GMT start/end datetimes."""
    fmt = lambda d: d.strftime("%Y-%m-%dT%H:%M:%S.0000000")
    return {
        "id": event_id,
        "subject": f"Event {event_id}",
        "categories": [],
        "attendees": [],
        "start": {"dateTime": fmt(start_dt), "timeZone": "Etc/GMT"},
        "end": {"dateTime": fmt(end_dt), "timeZone": "Etc/GMT"},
    }


class TestGetCalendarEvents(unittest.TestCase):
    def test_uses_calendar_view_url_with_wide_window(self):
        mgr = _make_manager(ignore_after_min=75)
        with patch("loneworker_utils.requests.get") as mock_get:
            mock_get.return_value = _ok_response([])
            loneworker_utils.LoneWorkerManager.get_calendar_events(mgr, [])

        call = mock_get.call_args
        url = call.args[0]
        params = call.kwargs["params"]

        self.assertTrue(url.endswith("/calendarView"), url)
        self.assertIn("startDateTime", params)
        self.assertIn("endDateTime", params)

        # Window should span ~2 * ignore_after_min minutes, centred on now.
        start = datetime.fromisoformat(params["startDateTime"].rstrip("Z")).replace(tzinfo=dt.timezone.utc)
        end = datetime.fromisoformat(params["endDateTime"].rstrip("Z")).replace(tzinfo=dt.timezone.utc)
        width_min = (end - start).total_seconds() / 60
        self.assertEqual(int(width_min), 150)

        now = datetime.now(dt.timezone.utc)
        self.assertLess(abs((start - (now - timedelta(minutes=75))).total_seconds()), 5)
        self.assertLess(abs((end - (now + timedelta(minutes=75))).total_seconds()), 5)

    def test_passes_auth_headers(self):
        mgr = _make_manager()
        with patch("loneworker_utils.requests.get") as mock_get:
            mock_get.return_value = _ok_response([])
            loneworker_utils.LoneWorkerManager.get_calendar_events(mgr, [])

        self.assertEqual(mock_get.call_args.kwargs["headers"], mgr.headers)

    def test_returns_all_events_when_no_filters(self):
        mgr = _make_manager()
        now = datetime.now(dt.timezone.utc)
        events = [
            _event_at("a", now - timedelta(minutes=30), now + timedelta(minutes=30)),
            _event_at("b", now - timedelta(minutes=10), now + timedelta(minutes=50)),
        ]
        with patch("loneworker_utils.requests.get") as mock_get:
            mock_get.return_value = _ok_response(events)
            result = loneworker_utils.LoneWorkerManager.get_calendar_events(mgr, [])

        self.assertEqual([e["id"] for e in result], ["a", "b"])

    def test_applies_time_filter_client_side(self):
        mgr = _make_manager()
        now = datetime.now(dt.timezone.utc)
        # Three events: one inside the [-15, +15] start window, two outside.
        events = [
            _event_at("inside", now - timedelta(minutes=5), now + timedelta(minutes=55)),
            _event_at("too_early", now - timedelta(minutes=40), now + timedelta(minutes=20)),
            _event_at("too_late", now + timedelta(minutes=40), now + timedelta(minutes=100)),
        ]
        time_filters = [
            loneworker_utils.TimeFilter(minutes=-15, before_or_after="after", start_or_end="start"),
            loneworker_utils.TimeFilter(minutes=15, before_or_after="before", start_or_end="start"),
        ]
        with patch("loneworker_utils.requests.get") as mock_get:
            mock_get.return_value = _ok_response(events)
            result = loneworker_utils.LoneWorkerManager.get_calendar_events(mgr, time_filters)

        self.assertEqual([e["id"] for e in result], ["inside"])

    def test_follows_pagination(self):
        mgr = _make_manager()
        now = datetime.now(dt.timezone.utc)
        page1 = [_event_at("p1a", now - timedelta(minutes=20), now + timedelta(minutes=40))]
        page2 = [_event_at("p2a", now - timedelta(minutes=10), now + timedelta(minutes=50)),
                 _event_at("p2b", now, now + timedelta(minutes=30))]

        next_url = "https://graph.microsoft.com/v1.0/next-page-marker"
        with patch("loneworker_utils.requests.get") as mock_get:
            mock_get.side_effect = [
                _ok_response(page1, next_link=next_url),
                _ok_response(page2),
            ]
            result = loneworker_utils.LoneWorkerManager.get_calendar_events(mgr, [])

        self.assertEqual([e["id"] for e in result], ["p1a", "p2a", "p2b"])
        # Second call must hit the nextLink with no extra params, since the
        # nextLink already encodes the original query state.
        self.assertEqual(mock_get.call_args_list[1].args[0], next_url)
        self.assertIsNone(mock_get.call_args_list[1].kwargs["params"])

    def test_raises_on_http_error(self):
        mgr = _make_manager()
        with patch("loneworker_utils.requests.get") as mock_get:
            response = MagicMock(status_code=500, text="boom")
            mock_get.return_value = response
            with self.assertRaises(RuntimeError):
                loneworker_utils.LoneWorkerManager.get_calendar_events(mgr, [])


if __name__ == '__main__':
    unittest.main()