"""Read-only deterministic portion calculation for recipe demonstration data.

No inventory mutation. Conservative date gates; never equates inventory/date to safe-to-eat.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from src.config import BASE_DIR
from src.services.recipe_service import canonical

# Only conversions within the SAME physical dimension. Never assume a pack's mass.
UNITS = {
    'g': ('mass', Decimal('1')),
    'kg': ('mass', Decimal('1000')),
    'ml': ('volume', Decimal('1')),
    'l': ('volume', Decimal('1000')),
    'piece': ('piece', Decimal('1')),
}
DISPLAY = {'g': 'g', 'kg': 'kg', 'ml': 'mL', 'l': 'L', 'piece': '個'}


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
        return number if number.is_finite() and number > 0 else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def _amount(value: Decimal) -> float:
    return float(value.quantize(Decimal('0.001')))


def classify_item(item: dict, today: date | None = None) -> tuple[str, str]:
    """Return eligible / review / blocked, with explicit reason.

    A passed best-before is a quality-review state, not automatically unsafe.
    No date means not certified as safe and is eligible only with a caution.
    """
    today = today or date.today()
    if item.get('status', 'active') != 'active' or _decimal(item.get('quantity')) is None:
        return 'blocked', '非有效庫存或數量無效'
    if item.get('known_spoiled') is True:
        return 'blocked', '已知變質'
    expiry = item.get('expiry_date')
    if not expiry:
        return 'eligible', '無標示日期；使用前仍須確認保存狀況'
    try:
        days = (date.fromisoformat(str(expiry)) - today).days
    except ValueError:
        return 'blocked', '標示日期格式錯誤'
    label = item.get('date_label_type')
    if days < 0 and label == 'use_by':
        return 'blocked', '已超過 Use By，不能用於自動料理推薦'
    if days < 0:
        return 'review', '已超過 Best Before／不明日期類型；不自動選用，需人工確認'
    if label not in ('use_by', 'best_before'):
        return 'review', '日期類型未知；須人工確認後使用'
    return 'eligible', ('接近標示日期，仍須檢查保存狀態' if days <= 3 else '日期未逾期，仍須檢查保存狀態')


def recommend_for_servings(
    inventory_items: list[dict],
    servings: int = 2,
    *,
    recipe_file_path: str | Path | None = None,
    limit: int = 5,
    today: date | None = None,
    mode: str = 'balanced',
) -> list[dict]:
    if isinstance(servings, bool) or not isinstance(servings, int) or not 1 <= servings <= 12:
        raise ValueError('servings 必須是 1～12 的整數')
    if mode not in ('balanced', 'ready_now', 'expiry_first'):
        raise ValueError('mode 必須是 balanced、ready_now 或 expiry_first')
    today = today or date.today()
    path = Path(recipe_file_path) if recipe_file_path else BASE_DIR / 'data/knowledge_base/recipes.sample.json'
    recipes = json.loads(path.read_text(encoding='utf-8'))['recipes']
    eligible: dict[str, list[dict]] = defaultdict(list)
    excluded: list[dict] = []
    for item in inventory_items:
        category, note = classify_item(item, today)
        if category == 'eligible':
            eligible[canonical(item.get('name', ''))].append(item)
        else:
            excluded.append({'name': item.get('name'), 'status': category, 'reason': note})

    ranked = []
    for recipe in recipes:
        base_servings = recipe.get('base_servings')
        specs = recipe.get('ingredient_quantities')
        if not isinstance(base_servings, int) or base_servings < 1 or not isinstance(specs, list):
            continue  # Never invent numeric requirements for recipes without proper data.
        scale = Decimal(servings) / Decimal(base_servings)
        rows = []
        for spec in specs:
            name = str(spec.get('name', '')).strip()
            unit = spec.get('unit')
            quantity = _decimal(spec.get('quantity'))
            if not name or unit not in UNITS or quantity is None:
                rows.append({'ingredient': name, 'status': 'unknown', 'reason': '食譜需求數量／單位未定義'})
                continue
            req = quantity * scale
            dimension, factor = UNITS[unit]
            available = Decimal(0)
            uncertain_units = []
            for item in eligible.get(canonical(name), []):
                stock_unit = item.get('unit')
                qty = _decimal(item.get('quantity'))
                if stock_unit not in UNITS or qty is None or UNITS[stock_unit][0] != dimension:
                    uncertain_units.append(str(stock_unit or '未提供'))
                else:
                    available += qty * UNITS[stock_unit][1] / factor
            if available >= req:
                status = 'enough'
            elif uncertain_units:
                status = 'unknown'
            else:
                status = 'missing' if available == 0 else 'insufficient'
            rows.append({
                'ingredient': name, 'required_quantity': _amount(req), 'available_quantity': _amount(available),
                'missing_quantity': _amount(max(Decimal(0), req - available)),
                'unit': unit, 'unit_label': DISPLAY[unit], 'status': status,
                'unconvertible_stock_units': sorted(set(uncertain_units)),
                'reason': ('庫存單位不可安全換算，需人工確認' if uncertain_units else ''),
            })
        if not rows: continue
        full = sum(row['status'] == 'enough' for row in rows)
        present = sum(row.get('available_quantity', 0) > 0 for row in rows)
        if not present: continue
        count = len(rows)
        urgency = Decimal(0)
        for row in rows:
            if row.get('available_quantity', 0) <= 0: continue
            for item in eligible.get(canonical(row['ingredient']), []):
                if item.get('expiry_date'):
                    days = (date.fromisoformat(str(item['expiry_date'])) - today).days
                    if 0 <= days <= 3:
                        urgency = max(urgency, Decimal(3 - days) / Decimal(4))
        coverage = Decimal(full) / Decimal(count)
        score = Decimal('0.65') * coverage + Decimal('0.35') * urgency
        ranked.append({
            'id': recipe['id'], 'title': recipe['title'], 'servings': servings,
            'base_servings': base_servings, 'ingredient_requirements': rows,
            'all_quantities_sufficient': all(row['status'] == 'enough' for row in rows),
            'score': round(float(score), 4), 'quantity_coverage': round(float(coverage), 3),
            'urgency_score': round(float(urgency), 3), 'excluded_items': excluded,
            'recipe_quantities_are_demo': True,
            'disclaimer': '食譜數量為專題示範假設，尚未核實標準食譜；日期與數量不能證明可安全食用。各料理獨立計算，若要同時製作多道料理須重新計算共享庫存。',
        })
    # ready_now: fully provisioned dishes first; expiry_first: prioritize near-date ingredients,
    # but never silently mark insufficient/unknown as ready. Original 'balanced' remains unchanged.
    if mode == 'ready_now':
        ranked.sort(key=lambda r: (not r['all_quantities_sufficient'], -r['score'], r['id']))
    elif mode == 'expiry_first':
        ranked.sort(key=lambda r: (-r['urgency_score'], -r['quantity_coverage'], r['id']))
    else:
        ranked.sort(key=lambda r: (-r['score'], r['id']))
    for result in ranked:
        result['recommendation_mode'] = mode
        result['can_make_now'] = result['all_quantities_sufficient']
        result['needs_manual_quantity_check'] = any(
            row['status'] == 'unknown' for row in result['ingredient_requirements']
        )
        result['priority_note'] = (
            '數量完整，但使用前仍需確認實際保存與食品安全' if result['can_make_now']
            else '未備齊或單位待確認；不可聲稱可直接製作'
        )
    return ranked[:max(1, min(limit, 20))]
