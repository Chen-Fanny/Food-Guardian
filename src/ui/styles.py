"""Small shared presentation helpers; no persistence or business rules."""

import logging
from html import escape
from pathlib import Path

import streamlit as st

from src.constants import DATE_LABEL_LABELS, NO_DATE_LABEL, UNIT_LABELS

LOGGER = logging.getLogger(__name__)
COLORS = {
    "primary": ("#2E7D32", "#E8F5E9"),
    "normal": ("#027A48", "#ECFDF3"),
    "expiring_soon": ("#925600", "#FFF4E5"),
    "passed_date": ("#B42318", "#FEF3F2"),
    "no_date": ("#667085", "#F2F4F7"),
    "historical": ("#667085", "#F2F4F7"),
}
DATE_STATUS_LABELS = {
    "normal": "✓ 正常",
    "expiring_soon": "● 即將到期",
    "passed_date": "! 已超過日期",
    "no_date": "— 未設定日期",
    "historical": "— 歷史紀錄",
}
NAV_PAGES = ("🏠 首頁", "📦 食材庫存", "🔔 日期提醒", "🤖 AI 餐點推薦", "📊 浪費統計")


def apply_styles():
    css = Path(__file__).with_name("styles.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def page_header(title, subtitle, action=None):
    with st.container(horizontal=True, vertical_alignment="center", gap="large"):
        with st.container():
            st.title(title)
            st.caption(subtitle)
        if action:
            with st.container(width=160):
                action()


def kpis(values):
    """Render a compact responsive grid of counts, always labeled in text."""
    cards = []
    for label, value, status, hint in values:
        color, _ = COLORS[status]
        cards.append(
            f'<div class="fg-kpi" style="--accent:{color}">'
            f'<span class="fg-kpi-label">{escape(label)}</span>'
            f'<strong>{value}</strong><span class="fg-muted">{escape(hint)}</span></div>'
        )
    st.markdown(
        '<div class="fg-kpis">' + "".join(cards) + "</div>", unsafe_allow_html=True
    )


def badge(status, label=None):
    color, background = COLORS[status]
    return (
        f'<span class="fg-badge" style="color:{color};background:{background}">'
        f"{escape(label or DATE_STATUS_LABELS[status])}</span>"
    )


def quantity_label(item):
    return f"{item['quantity']:g} {UNIT_LABELS[item['unit']]}"


def date_label(item):
    if not item["expiry_date"]:
        return NO_DATE_LABEL
    return (
        f"{DATE_LABEL_LABELS.get(item['date_label_type'], '')} · {item['expiry_date']}"
    )


def days_label(days):
    if days is None:
        return NO_DATE_LABEL
    if days < 0:
        return f"已超過輸入日期 {abs(days)} 天"
    if days == 0:
        return "輸入日期為今天"
    return f"剩餘 {days} 天"


def empty_state(title, description, symbol="—"):
    st.markdown(
        f'<div class="fg-empty"><span class="fg-empty-symbol">{escape(symbol)}</span>'
        f"<h3>{escape(title)}</h3><p>{escape(description)}</p></div>",
        unsafe_allow_html=True,
    )


def show_error(exc, *, action="讀取資料"):
    """Log diagnostics, but show recovery instructions rather than exceptions."""
    LOGGER.warning("%s failed", action, exc_info=True)
    if isinstance(exc, LookupError):
        message = "這筆食材已不存在，請重新整理頁面並選擇其他食材。"
    elif isinstance(exc, ValueError):
        message = "資料未能儲存。請確認欄位、目前庫存數量與紀錄狀態後重試。"
    else:
        message = (
            "暫時無法存取食材資料，請稍後重新整理；若持續發生，請確認資料夾的讀寫權限。"
        )
    st.error(message)


def show_flash():
    message = st.session_state.pop("ui_flash", None)
    if message:
        st.toast("✓ " + message)
