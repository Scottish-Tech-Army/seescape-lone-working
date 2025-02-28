import logging
import re
import sys
import types
import unittest
from datetime import datetime

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
        filter_str = loneworker_utils.build_time_filter(past_min, future_min, "start")
        # Check that the filter string mentions "start/dateTime" and today's date.
        today = datetime.now().strftime('%Y-%m-%d')
        self.assertIn("start/dateTime ge", filter_str)
        self.assertIn(today, filter_str)
        # Validate the complete pattern. Example:
        pattern = (
            r"start/dateTime ge '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z' "
            r"and start/dateTime le '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z'"
        )
        self.assertRegex(filter_str, pattern)

    def test_build_time_filter_end(self):
        past_min = 5
        future_min = 15
        filter_str = loneworker_utils.build_time_filter(past_min, future_min, "end")
        # Check that the filter string mentions "end/dateTime" and today's date.
        today = datetime.now().strftime('%Y-%m-%d')
        self.assertIn("end/dateTime ge", filter_str)
        self.assertIn(today, filter_str)
        # Validate the complete pattern. Example:
        pattern = (
            r"end/dateTime ge '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z' "
            r"and end/dateTime le '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z'"
        )
        self.assertRegex(filter_str, pattern)

if __name__ == '__main__':
    unittest.main()