"""Read-only adapter for ranked recipes."""
from typing import Any, Dict, List, Optional
from src.services.recipe_service import RecipeService

def match_recipes_from_inventory(ingredient_list: List[str], *, inventory_items: Optional[List[Dict[str, Any]]]=None, recipe_service: Optional[RecipeService]=None) -> List[Dict[str,Any]]:
    return (recipe_service or RecipeService()).recommend_recipes(ingredient_list,inventory_items=inventory_items)
