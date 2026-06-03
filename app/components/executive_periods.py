"""
Executive KPI period breakdown — month/week tables under the KPI cluster.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import polars as pl
import streamlit as st

from app.components.terminal import dataframe_table, money

_MONTH_LABELS = {
    "2026-01": "Jan 2026",
    "2026-02": "Fev 2026",
    "2026-03": "Mar 2026",
    "2026-04": "Abr 2026",
    "2026-05": "Mai 2026",
    "2026-06": "Jun 2026",
    "2026-07": "Jul 2026",
    "2026-08": "Ago 2026",
    "2026-09": "Set 2026",
    "2026-10": "Out 2026",
    "2026-11": "Nov 2026",
    "2026-12": "Dez 2026",
}
_WEEK_MONTHS = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")


def _period_label(period_key: str, grain: str) -> str:
    if grain == "month":
        return _MONTH_LABELS.get(period_key, period_key)
    try:
        year_s, week_s = period_key.split("-W", 1)
        week_n = int(week_s)
        start = datetime.fromisocalendar(int(year_s), week_n, 1)
        return f"W{week_n} · {start.day} {_WEEK_MONTHS[start.month - 1]}"
    except (TypeError, ValueError):
        return period_key


def _sales_quality_note(months_df: pl.DataFrame, weeks_df: pl.DataFrame) -> str | None:
    """Flag months/weeks where daily sales look like even-spread estimates."""
    try:
        from app.db import get_conn

        conn = get_conn()
        flags = conn.execute("""
            WITH daily AS (
                SELECT
                    strftime(CAST(Date AS DATE), '%Y-%m') AS mes,
                    CAST(Date AS DATE) AS d,
                    ROUND(SUM(CAST(REPLACE(CAST(Total AS VARCHAR), ',', '.') AS DOUBLE)), 2) AS rev
                FROM sales
                GROUP BY mes, d
            ),
            stats AS (
                SELECT mes,
                       COUNT(*) AS days,
                       COUNT(DISTINCT rev) AS distinct_rev
                FROM daily
                GROUP BY mes
            )
            SELECT mes FROM stats
            WHERE days >= 5 AND distinct_rev <= 2
            ORDER BY mes
        """).fetchall()
        conn.close()
    except Exception:
        return None

    if not flags:
        return None
    months = ", ".join(r[0] for r in flags)
    return (
        f"Estimated daily spread detected for: {months}. "
        "Month/week revenue totals match imports, but day-level splits are not real POS days. "
        "**You need daily Loyverse item-sales-summary CSVs (one file per day)** for true month-to-month velocity."
    )


def _period_table(df: pl.DataFrame, grain: str) -> pd.DataFrame:
    if df.is_empty():
        return pd.DataFrame()

    rows = []
    for r in df.iter_rows(named=True):
        key = str(r.get("period_key") or "")
        rows.append(
            {
                "Period": _period_label(key, grain),
                "Revenue": money(float(r.get("receita") or 0), 0),
                "Margin": f"{float(r.get('margin_pct') or 0):.1f}%",
                "Turnover": f"{float(r.get('avg_turnover') or 0):.2f}x",
                "Sell-through": f"{float(r.get('sell_through') or 0):.1f}%",
                "Avg Ticket": money(float(r.get("ticket") or 0), 2),
                "Low Stock": "—",
                "Ops": "—",
                "Fixed Burn": f"{float(r.get('burn_ratio') or 0):.1f}%",
            }
        )
    return pd.DataFrame(rows)


def render_executive_period_panel(months_df: pl.DataFrame, weeks_df: pl.DataFrame) -> None:
    """Render Month | Week tabs below the Period Breakdown panel header."""
    month_tab, week_tab = st.tabs(["Month", "Week"])

    with month_tab:
        table = _period_table(months_df, "month")
        if table.empty:
            st.caption("No monthly sales data.")
        else:
            st.markdown(dataframe_table(table, max_rows=12), unsafe_allow_html=True)

    with week_tab:
        table = _period_table(weeks_df, "week")
        if table.empty:
            st.caption("No weekly sales data.")
        else:
            st.markdown(dataframe_table(table, max_rows=12), unsafe_allow_html=True)

    st.caption(
        "Low stock and ops efficiency are current-state only (shown as —). "
        "Turnover and sell-through use current inventory as denominator."
    )
    quality = _sales_quality_note(months_df, weeks_df)
    if quality:
        st.warning(quality)
