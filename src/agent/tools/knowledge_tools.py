"""Read-only adapter for structured food knowledge."""
from typing import Any, Dict, Optional
from src.services.knowledge_service import KnowledgeService

def get_food_preservation_info(item_name: str, *, knowledge_service: Optional[KnowledgeService]=None) -> Optional[Dict[str, Any]]:
    return (knowledge_service or KnowledgeService()).lookup_item(item_name)
