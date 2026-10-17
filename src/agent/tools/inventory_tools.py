"""
Inventory Tools for AI Agent.
Enables the agent to inspect active inventory and expiring ingredients.
[Status: Planned]
"""

from typing import Any, Dict, List


def query_active_inventory(category: str = "") -> List[Dict[str, Any]]:
    """
    Tool function: Retrieve active inventory items from SQLite database.
    [Planned - To be implemented during development phase]
    """
    raise NotImplementedError("Tool query_active_inventory is under development.")


def query_expiring_items(days_ahead: int = 3) -> List[Dict[str, Any]]:
    """
    Tool function: Retrieve ingredients nearing expiration.
    [Planned - To be implemented during development phase]
    """
    raise NotImplementedError("Tool query_expiring_items is under development.")
