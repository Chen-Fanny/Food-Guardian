"""Prioritized date reminders; calculation remains in ReminderService."""

from html import escape

import streamlit as st

from src.constants import (
    DATE_DISCLAIMER,
    DEFAULT_WARNING_THRESHOLD_DAYS,
    PASSED_DATE_MESSAGES,
    STORAGE_LABELS,
    WARNING_THRESHOLD_OPTIONS,
)
from src.services.reminder_service import ReminderService
from src.ui.styles import (
    COLORS,
    badge,
    date_label,
    days_label,
    empty_state,
    page_header,
    quantity_label,
)


def render_priority_items(items):
    for item in items:
        status = item["reminder_status"]
        # Best Before is quality information: use a restrained neutral accent.
        visual_status = (
            "no_date"
            if status == "passed_date" and item["date_label_type"] == "best_before"
            else status
        )
        color, _ = COLORS[visual_status]
        message = (
            PASSED_DATE_MESSAGES.get(item["date_label_type"], "")
            if status == "passed_date"
            else ""
        )
        st.markdown(
            f'<div class="fg-food" style="--accent:{color}">'
            f'<div class="fg-food-header"><span class="fg-food-name">{escape(item["name"])}</span>'
            f'{badge(visual_status, "! 已超過日期" if status=="passed_date" else None)}</div>'
            f'<p class="fg-date">{escape(date_label(item))} · {escape(days_label(item["days_remaining"]))}</p>'
            f'<p>{escape(STORAGE_LABELS[item["storage_location"]])} · {escape(quantity_label(item))}</p>'
            + (f'<p class="fg-guidance">{escape(message)}</p>' if message else "")
            + "</div>",
            unsafe_allow_html=True,
        )


def render_reminders_view(inventory_service=None):
    def threshold_input():
        st.selectbox(
            "提醒範圍",
            WARNING_THRESHOLD_OPTIONS,
            index=WARNING_THRESHOLD_OPTIONS.index(DEFAULT_WARNING_THRESHOLD_DAYS),
            format_func=lambda n: f"{n} 天",
            key="reminder_threshold",
        )

    page_header("日期提醒", "優先查看近期需要注意的食材。", threshold_input)
    threshold = st.session_state["reminder_threshold"]
    with st.spinner("正在整理日期提醒…"):
        items = ReminderService(
            threshold, inventory_service=inventory_service
        ).get_items_with_days_remaining()
    st.caption(DATE_DISCLAIMER)
    st.subheader("需要優先注意")
    passed = sorted(
        [i for i in items if i["reminder_status"] == "passed_date"],
        key=lambda i: i["expiry_date"],
    )
    soon = sorted(
        [i for i in items if i["reminder_status"] == "expiring_soon"],
        key=lambda i: i["expiry_date"],
    )
    if not passed and not soon:
        empty_state(
            "目前沒有需要特別注意的食材。",
            "未設定日期的食材不會列入提醒，可至庫存頁補充日期。",
            "✓",
        )
    if passed:
        st.markdown(f"### 已超過日期 · {len(passed)} 筆")
        render_priority_items(passed)
    if soon:
        st.markdown(f"### 即將到期 · {len(soon)} 筆")
        render_priority_items(soon)
    normal = [i for i in items if i["reminder_status"] == "normal"]
    with st.expander(f"正常食材 · {len(normal)} 筆", expanded=False):
        if normal:
            render_priority_items(normal)
        else:
            st.caption("目前沒有此分類的食材。")
    st.caption(
        f'另有 {sum(i["reminder_status"]=="no_date" for i in items)} 筆未設定日期，請至食材庫存頁查看。'
    )
