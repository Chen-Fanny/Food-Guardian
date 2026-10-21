"""Shared ISO date parsing and remaining-day calculations."""

from datetime import date
from typing import Optional, Union


def parse_date(date_str: str) -> date:
    """Parse a calendar date in exactly YYYY-MM-DD format."""
    if not isinstance(date_str, str):
        raise ValueError("日期必須為 YYYY-MM-DD。")
    result = date.fromisoformat(date_str)
    if result.isoformat() != date_str:
        raise ValueError("日期必須為 YYYY-MM-DD。")
    return result


def calculate_days_remaining(
    target_date: Optional[Union[str, date]],
    today: Optional[date] = None,
) -> Optional[int]:
    """Return calendar-day difference, or None for an unset date."""
    if target_date is None:
        return None
    if isinstance(target_date, str):
        target_date = parse_date(target_date)
    return (target_date - (today if today is not None else date.today())).days
