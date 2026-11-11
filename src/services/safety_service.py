"""Read-only SQLite inventory safety triage, never a food safety certification."""
from __future__ import annotations
from datetime import date
from typing import Any
from src.services.portion_service import classify_item
from src.services.recipe_service import canonical


def assess_inventory_safety(items: list[dict[str, Any]], *, item_name: str = '', today: date | None = None) -> dict:
    if not isinstance(item_name, str) or len(item_name) > 80:
        raise ValueError('item_name 必須是 80 字內的食材名稱')
    today = today or date.today()
    matched = [item for item in items if not item_name.strip() or canonical(str(item.get('name', ''))) == canonical(item_name.strip())]
    rows = []
    for item in matched:
        status, reason = classify_item(item, today=today)
        rows.append({
            'inventory_id': item.get('id'), 'name': item.get('name'),
            'quantity': item.get('quantity'), 'unit': item.get('unit'),
            'expiry_date': item.get('expiry_date'), 'date_label_type': item.get('date_label_type'),
            'status': status, 'reason': reason,
            'allow_auto_recommendation': status == 'eligible',
        })
    return {
        'query': item_name, 'found': bool(rows), 'items': rows,
        'counts': {k: sum(row['status'] == k for row in rows) for k in ('eligible', 'review', 'blocked')},
        'scope': '僅檢查 SQLite 中目前有效庫存；不是食品安全認證',
        'disclaimer': '日期及外觀不能保證食物安全；超過 Use By 或已知變質不得自動推薦。對未知日期或 Best Before 過期採人工確認。',
    }
