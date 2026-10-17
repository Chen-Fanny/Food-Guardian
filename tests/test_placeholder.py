"""
Initial smoke test for project scaffold validation.
"""

import unittest
from datetime import date
from src.utils.helpers import parse_date, calculate_days_remaining


class TestScaffoldHelpers(unittest.TestCase):
    """Test utility helper functions."""

    def test_parse_date(self):
        d = parse_date("2026-10-17")
        self.assertEqual(d, date(2026, 10, 17))

    def test_calculate_days_remaining(self):
        # Calculation from today
        today_str = date.today().strftime("%Y-%m-%d")
        self.assertEqual(calculate_days_remaining(today_str), 0)


if __name__ == "__main__":
    unittest.main()
