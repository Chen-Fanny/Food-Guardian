
"""Food Guardian - 食材使用與浪費統計"""

import pandas as pd
from src.database.db_manager import DatabaseManager


class AnalyticsService:

    def __init__(self, db_manager=None):
        self.db = db_manager or DatabaseManager()

    def load_logs(self):
        """讀取使用與丟棄紀錄"""
        with self.db.connection() as conn:
            rows = conn.execute("""
                SELECT item_name, category, quantity,
                       unit, action_type, reason, log_date
                FROM consumption_waste_logs
                ORDER BY log_date
            """).fetchall()

        return pd.DataFrame(
            [dict(row) for row in rows],
            columns=[
                "item_name", "category", "quantity",
                "unit", "action_type", "reason", "log_date"
            ]
        )

    def compute_waste_summary(self):
        """依食材名稱和單位計算使用與丟棄量"""
        df = self.load_logs()

        if df.empty:
            return pd.DataFrame(columns=[
                "item_name", "unit", "consumed",
                "wasted", "waste_rate"
            ])

        summary = df.pivot_table(
            index=["item_name", "unit"],
            columns="action_type",
            values="quantity",
            aggfunc="sum",
            fill_value=0
        ).reset_index()

        for action in ["consumed", "wasted"]:
            if action not in summary.columns:
                summary[action] = 0.0

        total = summary["consumed"] + summary["wasted"]

        summary["waste_rate"] = (
            summary["wasted"]
            .div(total.where(total != 0))
            .mul(100)
            .fillna(0)
        )

        return summary

    def get_waste_reduction_kpis(self):
        """計算整體操作次數及各單位浪費比例"""
        df = self.load_logs()

        if df.empty:
            return {
                "total_events": 0,
                "waste_events": 0,
                "by_unit": {}
            }

        result = {}

        for unit, group in df.groupby("unit"):
            consumed = group.loc[
                group["action_type"] == "consumed",
                "quantity"
            ].sum()

            wasted = group.loc[
                group["action_type"] == "wasted",
                "quantity"
            ].sum()

            total = consumed + wasted

            result[unit] = {
                "consumed": float(consumed),
                "wasted": float(wasted),
                "waste_rate": (
                    round(wasted / total * 100, 2)
                    if total > 0 else None
                )
            }

        return {
            "total_events": len(df),
            "waste_events": int(
                (df["action_type"] == "wasted").sum()
            ),
            "by_unit": result
        }

    
    def get_waste_reasons(self):
        """統計食材丟棄原因"""
        df = self.load_logs()

        if df.empty:
            return pd.DataFrame(columns=["reason", "count"])

        wasted = df[df["action_type"] == "wasted"].copy()

        wasted["reason"] = wasted["reason"].replace("", pd.NA)
        wasted["reason"] = wasted["reason"].fillna("未填寫")

        result = (
            wasted.groupby("reason")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )

        return result

    def get_daily_trends(self):
        """統計每日使用與丟棄操作次數"""
        df = self.load_logs()

        if df.empty:
            return pd.DataFrame(
                columns=["log_date", "consumed", "wasted"]
            )

        trends = df.pivot_table(
            index="log_date",
            columns="action_type",
            values="quantity",
            aggfunc="size",
            fill_value=0
        ).reset_index()

        for action in ["consumed", "wasted"]:
            if action not in trends.columns:
                trends[action] = 0

        return trends.sort_values("log_date")

