"""Inventory CRUD and atomic partial consumption/waste operations."""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from src.constants import (
    CATEGORY_OPTIONS,
    DATE_LABEL_OPTIONS,
    STATUS_OPTIONS,
    STORAGE_OPTIONS,
    UNIT_OPTIONS,
)
from src.database.db_manager import DatabaseManager
from src.utils.helpers import parse_date


class InventoryService:
    """Inventory access shared by UI and agent tools.

    Missing IDs raise LookupError; invalid input and completed-record mutations
    raise ValueError. A new item is always active. Status changes only through
    consume_item/waste_item. Services expect an initialized DatabaseManager.
    """

    FIELDS = (
        "name",
        "category",
        "quantity",
        "unit",
        "purchase_date",
        "expiry_date",
        "date_label_type",
        "opened_date",
        "storage_location",
    )

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager if db_manager is not None else DatabaseManager()

    @staticmethod
    def _positive_quantity(value: Any) -> Decimal:
        try:
            if isinstance(value, bool):
                raise ValueError("數量必須是大於 0 的有限數值。")
            amount = Decimal(str(value))
            if (
                not amount.is_finite()
                or amount <= 0
                or not (0 < float(amount) < float("inf"))
            ):
                raise ValueError("數量必須是大於 0 的有限數值。")
            return amount
        except (InvalidOperation, TypeError, OverflowError) as exc:
            raise ValueError("數量必須是大於 0 的有限數值。") from exc

    @staticmethod
    def _date(value: Any, field: str, optional: bool = False) -> Optional[str]:
        if optional and value is None:
            return None
        try:
            text = value.isoformat() if isinstance(value, date) else value
            return parse_date(text).isoformat()
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"{field} 必須為 YYYY-MM-DD 日期。") from exc

    def _validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(data)
        if not isinstance(result.get("name"), str) or not result["name"].strip():
            raise ValueError("食材名稱不可空白。")
        result["name"] = result["name"].strip()
        for field, options in (
            ("category", CATEGORY_OPTIONS),
            ("unit", UNIT_OPTIONS),
            ("storage_location", STORAGE_OPTIONS),
        ):
            if result.get(field) not in options:
                raise ValueError(f"{field} 必須使用固定選項。")
        result["quantity"] = float(self._positive_quantity(result.get("quantity")))
        result["purchase_date"] = self._date(
            result.get("purchase_date"), "purchase_date"
        )
        for field in ("expiry_date", "opened_date"):
            result[field] = self._date(result.get(field), field, optional=True)
        label = result.get("date_label_type")
        if label is not None and label not in DATE_LABEL_OPTIONS:
            raise ValueError("date_label_type 必須為 use_by 或 best_before。")
        if result["expiry_date"] is not None and label is None:
            raise ValueError("有到期日期時必須選擇日期標示類型。")
        result["date_label_type"] = label
        return result

    @staticmethod
    def _require_item(conn, item_id: int) -> Dict[str, Any]:
        row = conn.execute(
            "SELECT * FROM inventory_items WHERE id = ?", (item_id,)
        ).fetchone()
        if row is None:
            raise LookupError(f"找不到食材 ID {item_id}。")
        return dict(row)

    @staticmethod
    def _require_active(item: Dict[str, Any]) -> None:
        if item["status"] != "active" or item["quantity"] <= 0:
            raise ValueError("已完成的歷史紀錄僅供查看，不可編輯、刪除、使用或丟棄。")

    def add_item(self, item_data: Dict[str, Any]) -> int:
        if set(item_data) - set(self.FIELDS):
            raise ValueError("新增資料包含不可設定的欄位。")
        data = self._validate(item_data)
        with self.db.connection() as conn:
            cursor = conn.execute(
                """INSERT INTO inventory_items
                (name, category, quantity, unit, purchase_date, expiry_date,
                 date_label_type, opened_date, storage_location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                tuple(data[field] for field in self.FIELDS),
            )
            return cursor.lastrowid

    def get_items(
        self,
        status: Optional[str] = "active",
        category: Optional[str] = None,
        storage_location: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        for value, options, field in (
            (status, STATUS_OPTIONS, "status"),
            (category, CATEGORY_OPTIONS, "category"),
            (storage_location, STORAGE_OPTIONS, "storage_location"),
        ):
            if value is not None and value not in options:
                raise ValueError(f"無效的 {field}。")
        with self.db.connection() as conn:
            rows = conn.execute(
                """SELECT * FROM inventory_items
                WHERE (? IS NULL OR status = ?)
                  AND (? IS NULL OR category = ?)
                  AND (? IS NULL OR storage_location = ?)
                ORDER BY id""",
                (
                    status,
                    status,
                    category,
                    category,
                    storage_location,
                    storage_location,
                ),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_item_by_id(self, item_id: int) -> Dict[str, Any]:
        with self.db.connection() as conn:
            return self._require_item(conn, item_id)

    def update_item(self, item_id: int, updates: Dict[str, Any]) -> bool:
        if set(updates) - set(self.FIELDS):
            raise ValueError("更新資料包含不可修改的欄位；狀態由使用／丟棄操作管理。")
        with self.db.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            item = self._require_item(conn, item_id)
            self._require_active(item)
            data = self._validate({**item, **updates})
            conn.execute(
                """UPDATE inventory_items SET name=?, category=?, quantity=?, unit=?,
                purchase_date=?, expiry_date=?, date_label_type=?, opened_date=?,
                storage_location=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                tuple(data[field] for field in self.FIELDS) + (item_id,),
            )
        return True

    def delete_item(self, item_id: int) -> bool:
        """Hard delete an active input error; existing logs retain snapshots."""
        with self.db.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._require_active(self._require_item(conn, item_id))
            conn.execute("DELETE FROM inventory_items WHERE id = ?", (item_id,))
        return True

    def consume_item(self, item_id: int, quantity: float) -> bool:
        return self._record_action(item_id, quantity, "consumed")

    def waste_item(
        self, item_id: int, quantity: float, reason: Optional[str] = None
    ) -> bool:
        if reason is not None and not isinstance(reason, str):
            raise ValueError("丟棄原因必須為文字。")
        return self._record_action(item_id, quantity, "wasted", reason)

    def _record_action(self, item_id, quantity, action, reason=None) -> bool:
        amount = self._positive_quantity(quantity)
        with self.db.connection() as conn:
            # Serialize reads and writes to prevent simultaneous over-consumption.
            conn.execute("BEGIN IMMEDIATE")
            item = self._require_item(conn, item_id)
            self._require_active(item)
            available = Decimal(str(item["quantity"]))
            if amount > available:
                raise ValueError("使用／丟棄數量不可超過現有庫存。")
            remaining = available - amount
            if remaining > 0 and float(remaining) == float(available):
                raise ValueError("操作數量過小，超出 SQLite 庫存數量可表示的精度。")
            conn.execute(
                """UPDATE inventory_items SET quantity=?, status=?,
                updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (float(remaining), action if remaining == 0 else "active", item_id),
            )
            conn.execute(
                """INSERT INTO consumption_waste_logs
                (item_id,item_name,category,quantity,unit,action_type,reason,log_date)
                VALUES (?,?,?,?,?,?,?,?)""",
                (
                    item_id,
                    item["name"],
                    item["category"],
                    float(amount),
                    item["unit"],
                    action,
                    reason,
                    date.today().isoformat(),
                ),
            )
        return True
