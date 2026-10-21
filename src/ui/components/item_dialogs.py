"""Focused native Streamlit dialogs. Mutations only call existing Service APIs."""

import sqlite3
from datetime import date
from decimal import Decimal

import streamlit as st

from src.constants import (
    CATEGORY_LABELS,
    CATEGORY_OPTIONS,
    UNIT_LABELS,
    UNIT_OPTIONS,
    STORAGE_LABELS,
    STORAGE_OPTIONS,
    DATE_LABEL_LABELS,
    DATE_LABEL_OPTIONS,
    WASTE_REASON_LABELS,
)
from src.ui.styles import quantity_label, show_error
from src.utils.helpers import parse_date

ERRORS = (ValueError, LookupError, sqlite3.Error, OSError)


def dismiss_dialog():
    st.session_state.pop("ui_dialog", None)


def _cancel():
    dismiss_dialog()
    st.rerun()


def _finish(message):
    dismiss_dialog()
    st.session_state["ui_flash"] = message
    st.rerun()


def _save(operation, message, *args, **kwargs):
    try:
        with st.spinner("正在更新食材…"):
            operation(*args, **kwargs)
    except ERRORS as exc:
        show_error(exc, action="更新食材")
    else:
        _finish(message)


def _prefix(action):
    return f"{action}_{st.session_state.get('dialog_nonce', 0)}"


def _item_fields(service, item=None):
    item = item or {}
    prefix = _prefix("edit" if item else "add")

    def choose(label, field, options, labels, **kwargs):
        value = item.get(field)
        index = options.index(value) if value in options else 0
        return st.selectbox(
            label,
            options,
            index=index,
            format_func=labels.get,
            key=f"{prefix}_{field}",
            **kwargs,
        )

    def optional_date(label, field):
        value = item.get(field)
        return st.date_input(
            label, value=parse_date(value) if value else None, key=f"{prefix}_{field}"
        )

    st.caption("帶有「必填」的欄位請完整填寫；到期與開封日期可留空。")
    st.subheader("基本資料")
    cols = st.columns(2)
    with cols[0]:
        name = st.text_input(
            "食材名稱（必填）", value=item.get("name", ""), key=f"{prefix}_name"
        )
        name_error = st.empty()
    with cols[1]:
        category = choose("分類", "category", CATEGORY_OPTIONS, CATEGORY_LABELS)
    st.subheader("數量")
    cols = st.columns(2)
    with cols[0]:
        quantity = st.number_input(
            "數量（必填）",
            min_value=0.0,
            value=float(item.get("quantity", 1)),
            step=1.0,
            key=f"{prefix}_quantity",
            format="%g",
        )
        quantity_error = st.empty()
    with cols[1]:
        unit = choose("單位", "unit", UNIT_OPTIONS, UNIT_LABELS)
    st.subheader("保存與日期")
    cols = st.columns(2)
    with cols[0]:
        storage = choose(
            "保存位置", "storage_location", STORAGE_OPTIONS, STORAGE_LABELS
        )
    with cols[1]:
        purchase = st.date_input(
            "購買日期",
            value=parse_date(item["purchase_date"]) if item else date.today(),
            key=f"{prefix}_purchase",
        )
    cols = st.columns(2)
    with cols[0]:
        expiry = optional_date("到期日期（可不填）", "expiry_date")
    with cols[1]:
        label = choose(
            "日期標示類型",
            "date_label_type",
            DATE_LABEL_OPTIONS,
            DATE_LABEL_LABELS,
            disabled=expiry is None,
            help="未填到期日期時，不需要日期標示類型。",
        )
    opened = optional_date("實際開封日期（可不填）", "opened_date")
    st.divider()
    with st.container(horizontal=True):
        if st.button("取消", key=f"{prefix}_cancel"):
            _cancel()
        submitted = st.button(
            "儲存修改" if item else "新增食材", type="primary", key=f"{prefix}_save"
        )
    if submitted:
        valid = True
        if not name.strip():
            name_error.error("請填寫食材名稱。")
            valid = False
        if quantity <= 0:
            quantity_error.error("請輸入大於 0 的數量。")
            valid = False
        if valid:
            data = dict(
                name=name,
                category=category,
                quantity=quantity,
                unit=unit,
                purchase_date=purchase,
                expiry_date=expiry,
                date_label_type=label if expiry is not None else None,
                opened_date=opened,
                storage_location=storage,
            )
            if item:
                _save(service.update_item, "食材資料已更新", item["id"], data)
            else:
                _save(service.add_item, "食材已新增", data)


@st.dialog("新增食材", width="medium", on_dismiss=dismiss_dialog)
def _add_dialog(service):
    _item_fields(service)


@st.dialog("編輯食材", width="medium", on_dismiss=dismiss_dialog)
def _edit_dialog(service, item):
    _item_fields(service, item)


def _quantity_action(service, item, *, waste):
    prefix = _prefix("waste" if waste else "consume")
    st.subheader(item["name"])
    st.caption(f"目前庫存：{quantity_label(item)}")
    amount = st.number_input(
        "本次丟棄" if waste else "本次使用",
        min_value=0.0,
        value=0.0,
        step=1.0,
        key=f"{prefix}_amount",
        format="%g",
    )
    valid = 0 < amount <= item["quantity"]
    if amount > item["quantity"]:
        st.error("數量超過目前庫存，請調整後再確認。")
    elif amount == 0:
        st.caption("請輸入大於 0 的數量。")
    reason = None
    if waste:
        reason = st.selectbox(
            "丟棄原因（可不填）",
            tuple(WASTE_REASON_LABELS),
            format_func=WASTE_REASON_LABELS.get,
            key=f"{prefix}_reason",
        )
    remaining = Decimal(str(item["quantity"])) - Decimal(str(amount))
    st.metric(
        "更新後剩餘",
        f"{remaining.normalize():f} {UNIT_LABELS[item['unit']]}" if valid else "—",
    )
    if valid and remaining == 0:
        st.caption("本次操作後將成為歷史紀錄，僅供查看。")
    with st.container(horizontal=True):
        if st.button("取消", key=f"{prefix}_cancel"):
            _cancel()
        with st.container(key="waste-confirm" if waste else "consume-confirm"):
            confirmed = st.button(
                "確認丟棄" if waste else "確認使用",
                type="secondary" if waste else "primary",
                disabled=not valid,
                key=f"{prefix}_confirm",
            )
    if confirmed:
        if waste:
            _save(
                service.waste_item, "已記錄食材丟棄", item["id"], amount, reason=reason
            )
        else:
            _save(service.consume_item, "已記錄食材使用", item["id"], amount)


@st.dialog("記錄已使用", on_dismiss=dismiss_dialog)
def _consume_dialog(service, item):
    _quantity_action(service, item, waste=False)


@st.dialog("記錄食材丟棄", on_dismiss=dismiss_dialog)
def _waste_dialog(service, item):
    _quantity_action(service, item, waste=True)


@st.dialog("刪除這筆庫存資料？", on_dismiss=dismiss_dialog)
def _delete_dialog(service, item):
    st.subheader(item["name"])
    st.caption(f"目前庫存：{quantity_label(item)}")
    st.write(
        "刪除僅適用於輸入錯誤的資料。若食材實際被使用或丟棄，請使用「已使用」或「已丟棄」功能。"
    )
    st.caption("此操作會永久刪除這筆庫存；既有使用／丟棄紀錄仍會保留。")
    with st.container(horizontal=True):
        if st.button("取消", key="cancel_delete"):
            _cancel()
        with st.container(key="danger-confirm"):
            confirmed = st.button("確認刪除", key="confirm_delete")
    if confirmed:
        _save(service.delete_item, "已刪除輸入錯誤的庫存", item["id"])


def open_item_dialog(action, item_id=None):
    """Keep a pending dialog across full reruns as well as native fragments."""
    st.session_state["dialog_nonce"] = st.session_state.get("dialog_nonce", 0) + 1
    st.session_state["ui_dialog"] = (action, item_id)


def render_pending_dialog(service):
    pending = st.session_state.get("ui_dialog")
    if pending is None:
        return
    action, item_id = pending
    if action == "add":
        _add_dialog(service)
        return
    try:
        item = service.get_item_by_id(item_id)
    except ERRORS as exc:
        dismiss_dialog()
        show_error(exc, action="讀取食材")
        return
    if item["status"] != "active" or item["quantity"] <= 0:
        dismiss_dialog()
        st.info("此食材已完成使用／丟棄，已成為歷史紀錄。請重新整理頁面。")
        return
    {
        "edit": _edit_dialog,
        "consume": _consume_dialog,
        "waste": _waste_dialog,
        "delete": _delete_dialog,
    }[action](service, item)
