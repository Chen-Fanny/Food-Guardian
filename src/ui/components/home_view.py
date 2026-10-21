"""A household inventory overview using existing reminder services."""

import streamlit as st

from src.constants import DATE_DISCLAIMER, DEFAULT_WARNING_THRESHOLD_DAYS
from src.services.reminder_service import ReminderService
from src.ui.components.item_dialogs import open_item_dialog
from src.ui.components.reminders_view import render_priority_items
from src.ui.styles import NAV_PAGES, empty_state, kpis, page_header


def go_to(page):
    st.session_state["navigation"] = page


def render_home(service):
    def add():
        if st.button("＋ 新增食材", type="primary", key="home_add"):
            open_item_dialog("add")

    st.markdown(
        '<div class="fg-eyebrow">好好保存，好好生活</div>',
        unsafe_allow_html=True,
    )
    page_header("Food Guardian", "更清楚掌握家中食材，優先使用快到期的食物。", add)
    with st.spinner("正在整理家中的食材…"):
        items = ReminderService(
            inventory_service=service
        ).get_items_with_days_remaining()
    kpis(
        [
            ("目前庫存", len(items), "primary", "使用中的食材筆數"),
            (
                "即將到期",
                sum(i["reminder_status"] == "expiring_soon" for i in items),
                "expiring_soon",
                f"{DEFAULT_WARNING_THRESHOLD_DAYS} 天內，包含今天",
            ),
            (
                "已超過日期",
                sum(i["reminder_status"] == "passed_date" for i in items),
                "passed_date",
                "依輸入日期計算",
            ),
            (
                "未設定日期",
                sum(i["reminder_status"] == "no_date" for i in items),
                "no_date",
                "可在庫存頁補充",
            ),
        ]
    )
    st.subheader("今天，先留意這些食材")
    priority = [
        i for i in items if i["reminder_status"] in ("passed_date", "expiring_soon")
    ]
    priority.sort(
        key=lambda i: (
            0 if i["reminder_status"] == "passed_date" else 1,
            i["expiry_date"],
            i["id"],
        )
    )
    if not items:
        empty_state(
            "從第一筆食材開始",
            "新增家中的食材，Food Guardian 就能協助你管理日期。",
            "＋",
        )
    elif not priority:
        empty_state(
            "目前沒有需要特別注意的食材。",
            "家中的食材日期已整理好，隨時可以查看完整庫存。",
            "✓",
        )
    else:
        render_priority_items(priority[:5])
        st.caption("最多顯示 5 筆優先項目；完整清單請至日期提醒。")
    with st.container(horizontal=True):
        st.button("查看食材庫存", on_click=go_to, args=(NAV_PAGES[1],))
        st.button("查看所有提醒", on_click=go_to, args=(NAV_PAGES[2],))
    st.divider()
    st.caption(DATE_DISCLAIMER)
    with st.expander("關於 Food Guardian"):
        st.write(
            "Food Guardian 是智慧家庭食材管理與減少食物浪費的課程專題。以庫存、日期提醒與後續 AI 輔助餐點建議，協助家庭更有效率地利用食材。"
        )
        st.caption("庫存與提醒已提供操作；AI Agent、食品知識查詢與浪費統計仍在開發中。")
