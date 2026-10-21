"""
Main Streamlit Application Entrypoint.
Food Guardian: A Knowledge-Guided AI Agent for Smart Food Inventory Management and Household Food Waste Reduction.
[Status: Inventory & Reminder validation; other modules planned]
"""

# Support the documented `streamlit run src/ui/app.py` entrypoint.
import sys
from pathlib import Path
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st  # noqa: E402

from src.database.db_manager import DatabaseManager  # noqa: E402
from src.services.inventory_service import InventoryService  # noqa: E402
from src.ui.components.inventory_view import render_inventory_view  # noqa: E402
from src.ui.components.reminders_view import render_reminders_view  # noqa: E402
from src.ui.components.agent_chat_view import render_agent_chat_view  # noqa: E402
from src.ui.components.analytics_view import render_analytics_view  # noqa: E402
from src.ui.components.home_view import render_home  # noqa: E402
from src.ui.styles import NAV_PAGES, apply_styles, show_error, show_flash  # noqa: E402


from src.ui.components import item_dialogs  # noqa: E402


def main():
    st.set_page_config(page_title="Food Guardian", page_icon="🥑", layout="wide")
    apply_styles()
    with st.sidebar:
        st.markdown(
            '<div class="fg-brand">🥑 Food Guardian</div>', unsafe_allow_html=True
        )
        st.caption("家中的食材，好好管理。")
        page = st.radio(
            "導覽",
            NAV_PAGES,
            key="navigation",
            label_visibility="collapsed",
            on_change=item_dialogs.dismiss_dialog,
        )
        st.divider()
        st.caption("課程專題 · 開發中")
        st.caption("AI 與浪費統計 · Under Development")
    show_flash()
    if page in NAV_PAGES[:3]:
        try:
            db = DatabaseManager()
            db.initialize_database()
        except (sqlite3.Error, OSError) as exc:
            show_error(exc, action="初始化資料")
            return
        service = InventoryService(db)
        try:
            if page == NAV_PAGES[0]:
                render_home(service)
            elif page == NAV_PAGES[1]:
                render_inventory_view(service)
            else:
                render_reminders_view(service)
            item_dialogs.render_pending_dialog(service)
        except (ValueError, LookupError, sqlite3.Error, OSError) as exc:
            show_error(exc)
            if st.button("重新載入"):
                st.rerun()
    elif page == "🤖 AI 餐點推薦":
        render_agent_chat_view()
    elif page == "📊 浪費統計":
        render_analytics_view()


if __name__ == "__main__":
    main()
