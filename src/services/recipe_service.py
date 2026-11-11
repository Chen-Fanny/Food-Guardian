"""Deterministic transparent recipe matching with food-date safeguards."""
import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.config import BASE_DIR

ENGLISH_ALIASES = {'Whole Milk':'牛奶','Fresh Spinach':'菠菜','Eggs':'雞蛋','Chicken Breast':'雞胸肉'}

def canonical(name: str) -> str:
    return ENGLISH_ALIASES.get(name.strip(),name.strip()).casefold()

class RecipeService:
    def __init__(self, recipe_file_path: Optional[str] = None):
        self.recipe_file_path = Path(recipe_file_path) if recipe_file_path else BASE_DIR / 'data/knowledge_base/recipes.sample.json'

    def recommend_recipes(self, available_items: List[str], inventory_items: Optional[List[Dict[str,Any]]] = None, limit: int = 5) -> List[Dict[str,Any]]:
        with self.recipe_file_path.open(encoding='utf-8') as fh:
            recipes = json.load(fh)['recipes']
        items = inventory_items if inventory_items is not None else [{'name':name,'status':'active','quantity':1} for name in available_items]
        safe_items = []
        excluded = []
        today = date.today()
        for item in items:
            if item.get('status','active') != 'active' or float(item.get('quantity',0)) <= 0:
                continue
            expiry = item.get('expiry_date')
            if expiry:
                try:
                    remaining = (date.fromisoformat(expiry)-today).days
                except ValueError:
                    excluded.append(item['name']); continue
                if remaining < 0:
                    excluded.append(item['name']); continue
                # A use-by date today should trigger caution; user must verify storage/condition.
            safe_items.append(item)
        names = {canonical(i['name']) for i in safe_items}
        ranked = []
        for r in recipes:
            needed = list(r['ingredients'])
            matched = [n for n in needed if canonical(n) in names]
            if not matched: continue
            missing = [n for n in needed if canonical(n) not in names]
            coverage = len(matched)/len(needed)
            urgency = 0.0
            for item in safe_items:
                if canonical(item['name']) in {canonical(n) for n in matched} and item.get('expiry_date'):
                    remaining = (date.fromisoformat(item['expiry_date'])-today).days
                    urgency = max(urgency, max(0.0, 1.0 - remaining/4)) if remaining <= 3 else urgency
            score = round(0.65*coverage + 0.35*urgency, 4)
            ranked.append({**r, 'matched_ingredients':matched,'missing_ingredients':missing,'match_rate':round(coverage,3),'urgency_score':round(urgency,3),'score':score, 'excluded_outdated_items':excluded,'reason': f'現有食材符合 {len(matched)}/{len(needed)} 項；' + ('包含接近標示日期的食材，應先確認保存與食用安全。' if urgency else '可利用現有庫存。')})
        return sorted(ranked,key=lambda x:(-x['score'],-x['match_rate'],x['id']))[:max(1,min(limit,20))]
