"""Calendar-date reminders without food safety conclusions."""

from datetime import date
from typing import Any, Dict, List, Optional

from src.constants import DEFAULT_WARNING_THRESHOLD_DAYS
from src.services.inventory_service import InventoryService
from src.utils.helpers import calculate_days_remaining


class ReminderService:
    """Classify active inventory dates; expiry_date=None is excluded from alerts."""

    def __init__(
        self,
        warning_threshold_days: int = DEFAULT_WARNING_THRESHOLD_DAYS,
        inventory_service: Optional[InventoryService] = None,
        today: Optional[date] = None,
    ):
        if (
            isinstance(warning_threshold_days, bool)
            or not isinstance(warning_threshold_days, int)
            or warning_threshold_days < 0
        ):
            raise ValueError("提醒天數必須為非負整數。")
        self.warning_threshold_days = warning_threshold_days
        self.inventory = (
            inventory_service if inventory_service is not None else InventoryService()
        )
        self.today = today

    def get_reminder_status(self, expiry_date) -> str:
        days = calculate_days_remaining(expiry_date, self.today)
        if days is None:
            return "no_date"
        if days < 0:
            return "passed_date"
        if days <= self.warning_threshold_days:
            return "expiring_soon"
        return "normal"

    def get_items_with_days_remaining(self) -> List[Dict[str, Any]]:
        items = self.inventory.get_items(status="active")
        for item in items:
            item["days_remaining"] = calculate_days_remaining(
                item["expiry_date"], self.today
            )
            item["reminder_status"] = self.get_reminder_status(item["expiry_date"])
        return items

    def get_expiring_soon(self) -> List[Dict[str, Any]]:
        return [
            item
            for item in self.get_items_with_days_remaining()
            if item["reminder_status"] == "expiring_soon"
        ]

    def get_expired_items(self) -> List[Dict[str, Any]]:
        """Return passed dates; the method name does not judge food safety."""
        return [
            item
            for item in self.get_items_with_days_remaining()
            if item["reminder_status"] == "passed_date"
        ]
