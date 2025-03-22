import logging
import os
import sys
import types
import unittest
from datetime import datetime

# Add the local src directories to the include path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))
# Dummy out boto3 so that loneworker_utils loads without trying to use boto3.
dummy_boto3 = types.ModuleType("boto3")
sys.modules["boto3"] = dummy_boto3

import loneworker_utils

class TestLoneworkerUtils(unittest.TestCase):
    def test_get_logger(self):
        logger = loneworker_utils.get_logger()
        self.assertIsInstance(logger, logging.Logger)
        self.assertTrue(callable(logger.info))

    def test_build_time_filter_start(self):
        past_min = 10
        future_min = 20
        time_filter = [
            loneworker_utils.TimeFilter(minutes=past_min, before_or_after="after", start_or_end="start"),
            loneworker_utils.TimeFilter(minutes=future_min, before_or_after="before", start_or_end="start")
        ]
        filter_str = loneworker_utils.build_time_filter(time_filter)
        # Check that the filter string mentions "start/dateTime" and today's date.
        today = datetime.now().strftime('%Y-%m-%d')
        self.assertIn("start/dateTime ge", filter_str)
        self.assertIn(today, filter_str)

    def test_build_time_filter_end(self):
        past_min = 5
        future_min = 15
        time_filters = [
            loneworker_utils.TimeFilter(minutes=past_min, before_or_after="after", start_or_end="end"),
            loneworker_utils.TimeFilter(minutes=future_min, before_or_after="before", start_or_end="end")
        ]
        filter_str = loneworker_utils.build_time_filter(time_filters)
        # Check that the filter string mentions "end/dateTime" and today's date.
        # Check that the filter string mentions "end/dateTime" and today's date.
        today = datetime.now().strftime('%Y-%m-%d')
        # Check that the filter string mentions "end/dateTime" and today's date.
        # Check that the filter string mentions "end/dateTime" and today's date.
        today = datetime.now().strftime('%Y-%m-%d')
        self.assertIn("end/dateTime ge", filter_str)
        self.assertIn(today, filter_str)

    def test_build_time_filter_invalid(self):
        past_min = 10
        future_min = 20
        with self.assertRaises(ValueError):
            loneworker_utils.build_time_filter([
                loneworker_utils.TimeFilter(minutes=past_min, before_or_after="after", start_or_end="invalid"),
                loneworker_utils.TimeFilter(minutes=future_min, before_or_after="before", start_or_end="invalid")
            ])

        with self.assertRaises(ValueError):
            loneworker_utils.build_time_filter([
                loneworker_utils.TimeFilter(minutes=past_min, before_or_after="after", start_or_end="start"),
                loneworker_utils.TimeFilter(minutes=future_min, before_or_after="invalid", start_or_end="end")
            ])

if __name__ == '__main__':
    unittest.main()