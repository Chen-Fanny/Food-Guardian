import streamlit as st
import plotly.express as px

from src.database.db_manager import DatabaseManager
from src.services.analytics_service import AnalyticsService


def render_analytics_view():
    st.title("📊 食材使用與浪費分析")
    st.caption("Food Guardian - Data Analytics Dashboard")

    db = DatabaseManager()
    db.initialize_database()
    analytics = AnalyticsService(db)

    summary = analytics.compute_waste_summary()
    kpis = analytics.get_waste_reduction_kpis()

    if summary.empty:
        st.info("目前沒有使用或丟棄紀錄，請先新增資料。")
        return

    st.subheader("整體操作統計")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("總操作次數", kpis["total_events"])

    with col2:
        st.metric("丟棄操作次數", kpis["waste_events"])

    st.subheader("各食材浪費比例")

    fig1 = px.bar(
        summary,
        x="item_name",
        y="waste_rate",
        color="item_name",
        labels={
            "item_name": "食材",
            "waste_rate": "浪費比例 (%)"
        },
        title="食材浪費比例比較"
    )

    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("食材使用與丟棄比較")

    unit = st.selectbox(
        "選擇單位",
        sorted(summary["unit"].unique())
    )

    filtered = summary[summary["unit"] == unit]

    fig2 = px.bar(
        filtered,
        x="item_name",
        y=["consumed", "wasted"],
        barmode="group",
        labels={
            "item_name": "食材",
            "value": f"數量 ({unit})",
            "variable": "類型"
        },
        title=f"食材使用與丟棄量（{unit}）"
    )

    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("詳細統計資料")
    st.dataframe(summary, use_container_width=True)
    
    st.divider()
    st.subheader("食材浪費原因分析")

    reasons = analytics.get_waste_reasons()

    if not reasons.empty:
        fig3 = px.bar(
            reasons,
            x="reason",
            y="count",
            labels={
                "reason": "丟棄原因",
                "count": "丟棄次數"
            },
            title="食材丟棄原因統計"
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("目前沒有食材丟棄紀錄。")

    st.divider()
    st.subheader("每日食材使用與丟棄趨勢")

    trends = analytics.get_daily_trends()

    if not trends.empty:
        trends["log_date"] = trends["log_date"].astype(str)

        fig4 = px.line(
            trends,
            x="log_date",
            y=["consumed", "wasted"],
            markers=True,
            labels={
                "log_date": "日期",
                "value": "操作次數",
                "variable": "類型"
            },
            title="每日使用與丟棄操作趨勢"
        )

        fig4.update_xaxes(type="category")
        fig4.update_yaxes(
            tickmode="linear",
            dtick=1,
            rangemode="tozero"
        )

        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("目前沒有可分析的歷史紀錄。")
