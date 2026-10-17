"""
Helper utility functions for date calculations, string formatters, and validation.
[Status: Under Development]
"""

from datetime import datetime, date
from typing import Union


def parse_date(date_str: str) -> date:
    """
    Parse ISO formatted date string (YYYY-MM-DD).
    """
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def calculate_days_remaining(target_date: Union[str, date]) -> int:
    """
    Calculate days remaining until target date from today.
    """
    if isinstance(target_date, str):
        target_date = parse_date(target_date)
    today = date.today()
    return (target_date - today).days
