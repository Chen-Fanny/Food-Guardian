"""Thin inventory adapters for Agent tools; no SQLite queries here."""

from typing import Any, Dict, List, Optional

from src.constants import DEFAULT_WARNING_THRESHOLD_DAYS
from src.database.db_manager import DatabaseManager
from src.services.inventory_service import InventoryService
from src.services.reminder_service import ReminderService


def _inventory(service: Optional[InventoryService]) -> InventoryService:
    if service is not None:
        return service
    db = DatabaseManager()
    db.initialize_database()
    return InventoryService(db)


def query_active_inventory(
    category: str = "",
    *,
    inventory_service: Optional[InventoryService] = None,
) -> List[Dict[str, Any]]:
    """Return active items, optionally filtered by a fixed category value."""
    return _inventory(inventory_service).get_items(
        status="active", category=category or None
    )


def query_expiring_items(
    days_ahead: int = DEFAULT_WARNING_THRESHOLD_DAYS,
    *,
    inventory_service: Optional[InventoryService] = None,
) -> List[Dict[str, Any]]:
    """Return dates from today through days_ahead, excluding passed/unset dates."""
    return ReminderService(
        days_ahead, _inventory(inventory_service)
    ).get_expiring_soon()
