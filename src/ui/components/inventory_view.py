"""Inventory dashboard; data and date classification use existing Services."""

from html import escape

import streamlit as st

from src.constants import (
    CATEGORY_LABELS,
    CATEGORY_OPTIONS,
    STATUS_LABELS,
    STATUS_OPTIONS,
    STORAGE_LABELS,
    STORAGE_OPTIONS,
    DEFAULT_WARNING_THRESHOLD_DAYS,
)
from src.utils.helpers import calculate_days_remaining
from src.services.inventory_service import InventoryService
from src.services.reminder_service import ReminderService
from src.ui.components.item_dialogs import open_item_dialog
from src.ui.styles import (
    DATE_STATUS_LABELS,
    badge,
    date_label,
    days_label,
    empty_state,
    kpis,
    page_header,
    quantity_label,
)


def inventory_rows(items, reminders):
    """A short list for scanning; full metadata lives in selected-item details."""
    rows = []
    for item in items:
        status = (
            reminders.get_reminder_status(item["expiry_date"])
            if item["status"] == "active"
            else "historical"
        )
        rows.append(
            {
                "食材名稱": item["name"],
                "數量": quantity_label(item),
                "保存位置": STORAGE_LABELS[item["storage_location"]],
                "日期": date_label(item),
                "剩餘天數": days_label(calculate_days_remaining(item["expiry_date"])),
                "日期狀態": DATE_STATUS_LABELS[status],
                "紀錄狀態": STATUS_LABELS[item["status"]],
            }
        )
    return rows


def _reset_filters():
    for key, value in (
        ("inventory_search", ""),
        ("inventory_category", None),
        ("inventory_storage", None),
        ("inventory_status", "active"),
    ):
        st.session_state[key] = value


def _toolbar():
    with st.container(horizontal=True, vertical_alignment="bottom", gap="small"):
        with st.container(width=260):
            search = st.text_input(
                "搜尋食材名稱", placeholder="輸入名稱，例如牛奶", key="inventory_search"
            )
        with st.container(width=160):
            category = st.selectbox(
                "篩選分類",
                (None,) + CATEGORY_OPTIONS,
                format_func=lambda x: "全部分類" if x is None else CATEGORY_LABELS[x],
                key="inventory_category",
            )
        with st.container(width=160):
            storage = st.selectbox(
                "篩選保存位置",
                (None,) + STORAGE_OPTIONS,
                format_func=lambda x: "全部位置" if x is None else STORAGE_LABELS[x],
                key="inventory_storage",
            )
        with st.container(width=140):
            status = st.selectbox(
                "篩選狀態",
                STATUS_OPTIONS + (None,),
                format_func=lambda x: "全部紀錄" if x is None else STATUS_LABELS[x],
                key="inventory_status",
            )
        st.button("重設篩選", on_click=_reset_filters)
    return search.strip().casefold(), category, storage, status


def _selected_item(items, service, reminders):
    by_id = {item["id"]: item for item in items}
    # Remove stale selections after deletion or a changed filter.
    if st.session_state.get("selected_item") not in by_id:
        st.session_state["selected_item"] = items[0]["id"]
    selected_id = st.selectbox(
        "選擇食材以查看詳情與操作",
        tuple(by_id),
        format_func=lambda key: f'#{key} {by_id[key]["name"]}',
        key="selected_item",
    )
    item = by_id[selected_id]
    completed = item["status"] != "active" or item["quantity"] <= 0
    status = (
        reminders.get_reminder_status(item["expiry_date"])
        if not completed
        else "historical"
    )
    visual_status = (
        "no_date"
        if status == "passed_date" and item["date_label_type"] == "best_before"
        else status
    )
    display_badge = badge(visual_status, DATE_STATUS_LABELS[status])
    st.markdown(
        f'<div class="fg-food-header"><span class="fg-food-name">{escape(item["name"])}</span>{display_badge}</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        f'{quantity_label(item)} · {CATEGORY_LABELS[item["category"]]} · {STORAGE_LABELS[item["storage_location"]]}'
    )
    if completed:
        st.info("此食材已完成使用／丟棄，已成為歷史紀錄。")
    else:
        st.caption(date_label(item))
    with st.container(horizontal=True, gap="small"):
        for action, label in (
            ("edit", "編輯"),
            ("consume", "已使用"),
            ("waste", "已丟棄"),
            ("delete", "刪除"),
        ):
            if st.button(label, key=f"{action}_item_{selected_id}", disabled=completed):
                open_item_dialog(action, selected_id)
    with st.expander("查看完整資料", expanded=False):
        st.write(f'購買日期：{item["purchase_date"]}')
        st.write(f"日期標示與到期日期：{date_label(item)}")
        st.write(f'實際開封日期：{item["opened_date"] or "未設定日期"}')
        st.write(f'紀錄狀態：{STATUS_LABELS[item["status"]]}')


def render_inventory_view(inventory_service=None):
    service = inventory_service if inventory_service is not None else InventoryService()
    reminders = ReminderService(inventory_service=service)

    def add():
        if st.button("＋ 新增食材", type="primary", key="inventory_add"):
            open_item_dialog("add")

    page_header("食材庫存", "查看、管理與更新家中的食材。", add)
    with st.spinner("正在整理食材庫存…"):
        active = reminders.get_items_with_days_remaining()
    kpis(
        [
            ("全部食材", len(active), "primary", "使用中的食材筆數"),
            (
                "冷藏",
                sum(i["storage_location"] == "refrigerator" for i in active),
                "normal",
                "冰箱中的日常食材",
            ),
            (
                "冷凍",
                sum(i["storage_location"] == "freezer" for i in active),
                "no_date",
                "冷凍保存的食材",
            ),
            (
                "即將到期",
                sum(i["reminder_status"] == "expiring_soon" for i in active),
                "expiring_soon",
                f"{DEFAULT_WARNING_THRESHOLD_DAYS} 天內，包含今天",
            ),
        ]
    )
    search, category, storage, status = _toolbar()
    items = service.get_items(
        status=status, category=category, storage_location=storage
    )
    if search:
        items = [item for item in items if search in item["name"].casefold()]
    if not items:
        # Distinguish a truly empty database from an empty filtered result.
        if not service.get_items(status=None):
            empty_state(
                "目前還沒有食材",
                "新增第一筆食材，Food Guardian 就能開始協助你管理日期。",
                "＋",
            )
            if st.button("＋ 新增第一筆食材", key="empty_add", type="primary"):
                open_item_dialog("add")
        else:
            empty_state(
                "沒有符合條件的食材", "試著修改搜尋文字，或重設篩選查看使用中的食材。"
            )
        return
    st.caption(
        f"找到 {len(items)} 筆食材 · 日期提醒以 {DEFAULT_WARNING_THRESHOLD_DAYS} 天為範圍"
    )
    st.dataframe(inventory_rows(items, reminders), hide_index=True, width="stretch")
    st.divider()
    _selected_item(items, service, reminders)
