"""
FulôFiló AI — Institutional Retail Operations Terminal
======================================================
Run: uv run streamlit run app/app.py
Access: http://localhost:8501
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import polars as pl
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.components.hud import HUD, hud_plotly_layout, inject_hud_css
from app.components.executive_periods import render_executive_period_panel
from app.components.sidebar import get_month_filter, render_sidebar
from app.components.terminal import (
    command_tape,
    dataframe_table,
    feed,
    kpi_grid,
    money,
    number,
    panel,
    render_terminal_css,
    status_bar,
    status_color,
    terminal_header,
)
from app.db import (
    get_abc_analysis,
    get_available_months,
    get_cashflow_summary,
    get_conn,
    get_daily_sales_trend,
    get_data_mtime,
    get_executive_monthly_breakdown,
    get_executive_weekly_breakdown,
    get_inventory_alerts,
    get_kpis_by_months,
    get_margin_matrix,
    get_monthly_breakdown,
    get_stock_turnover,
    get_summary_kpis,
)
from app.utils.fixed_costs import load_fixed_costs
from app.utils.reorder_engine import LEAD_TIME_DAYS, get_alerts
from app.utils.source_health import ROOT, STATUS_PATH, get_source_health, render_source_health_warning
from core.event_engine import detect_operational_events, enrich_reorder_alert, get_sku_velocity_stats
from core.ops_events import events_to_feed_rows, read_recent_events
from core.recommendations import build_decision_map_summary


_FAVICON = str(Path(__file__).resolve().parent / "assets" / "favicon.png")
st.set_page_config(
    page_title="FulôFiló AI Terminal",
    page_icon=_FAVICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_hud_css()
render_terminal_css()
render_sidebar(active_page="app.py")
render_source_health_warning()


def _f(value: object) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _last_sync_label() -> str:
    candidates = [
        STATUS_PATH,
        ROOT / "data" / "parquet" / "products.parquet",
        ROOT / "data" / "parquet" / "daily_sales.parquet",
        ROOT / "data" / "parquet" / "inventory.parquet",
        ROOT / "data" / "parquet" / "cashflow.parquet",
    ]
    mtimes = [p.stat().st_mtime for p in candidates if p.exists()]
    if not mtimes:
        return "never"
    return datetime.fromtimestamp(max(mtimes)).strftime("%Y-%m-%d %H:%M")


@st.cache_data
def load_terminal_data(data_version: str, selected_months: tuple[str, ...]):  # noqa: ARG001
    conn = get_conn()
    kpis = get_summary_kpis(conn)
    abc_df = get_abc_analysis(conn)
    margin_df = get_margin_matrix(conn)
    inventory_df = get_inventory_alerts(conn)
    turnover_df = get_stock_turnover(conn)
    cashflow_df = get_cashflow_summary(conn)
    sales_trend_df = get_daily_sales_trend(conn, top_n=8)
    available_months = get_available_months(conn)
    monthly_df = get_monthly_breakdown(conn, list(selected_months))
    if selected_months:
        revenue, units, ticket = get_kpis_by_months(conn, list(selected_months))
        kpis = (revenue, units, _f(kpis[2]) if kpis else 0.0, ticket)

    try:
        inventory_value = conn.execute("""
            SELECT SUM(CAST(i.current_stock AS DOUBLE) * COALESCE(p.unit_cost, 0)) AS inventory_value
            FROM inventory i
            LEFT JOIN products p ON lower(i.product) = lower(p.full_name)
        """).fetchone()[0]
    except Exception:
        inventory_value = 0.0

    try:
        payment_df = conn.execute("""
            SELECT Payment_Method, SUM(Total) AS revenue
            FROM sales
            GROUP BY Payment_Method
            ORDER BY revenue DESC
        """).pl()
    except Exception:
        payment_df = pl.DataFrame()

    try:
        latest_sales_df = conn.execute("""
            SELECT Date, Product, Quantity, Total, Payment_Method, Source
            FROM sales
            ORDER BY CAST(Date AS DATE) DESC, Product
            LIMIT 10
        """).pl()
    except Exception:
        latest_sales_df = pl.DataFrame()

    try:
        category_df = conn.execute("""
            SELECT category, SUM(revenue) AS revenue, SUM(profit) AS profit, SUM(qty_sold) AS units
            FROM products
            GROUP BY category
            ORDER BY revenue DESC
        """).pl()
    except Exception:
        category_df = pl.DataFrame()

    exec_months_df = get_executive_monthly_breakdown(conn)
    exec_weeks_df = get_executive_weekly_breakdown(conn)

    conn.close()
    return {
        "kpis": kpis,
        "abc": abc_df,
        "margin": margin_df,
        "inventory": inventory_df,
        "turnover": turnover_df,
        "cashflow": cashflow_df,
        "sales_trend": sales_trend_df,
        "available_months": available_months,
        "monthly": monthly_df,
        "exec_months": exec_months_df,
        "exec_weeks": exec_weeks_df,
        "inventory_value": _f(inventory_value),
        "payment": payment_df,
        "latest_sales": latest_sales_df,
        "category": category_df,
        "health": get_source_health(),
    }


selected_months = tuple(get_month_filter())
data = load_terminal_data(get_data_mtime(), selected_months)
health = data["health"].get("health", {})
readiness = str(health.get("readiness_state", "unknown")).upper()

revenue = _f(data["kpis"][0]) if data["kpis"] else 0.0
units = _f(data["kpis"][1]) if data["kpis"] else 0.0
profit = _f(data["kpis"][2]) if data["kpis"] else 0.0
ticket = _f(data["kpis"][3]) if data["kpis"] else 0.0
margin_pct = (profit / revenue * 100) if revenue else 0.0

inventory_pd = data["inventory"].to_pandas() if not data["inventory"].is_empty() else pd.DataFrame()
critical_count = int((inventory_pd.get("alert") == "🔴 Crítico").sum()) if not inventory_pd.empty else 0
low_count = int((inventory_pd.get("alert") == "🟡 Baixo").sum()) if not inventory_pd.empty else 0
total_skus = int(len(inventory_pd))
healthy_skus = int((inventory_pd.get("alert") == "🟢 OK").sum()) if not inventory_pd.empty else 0
ops_score = 100
ops_score -= min(35, critical_count * 7)
ops_score -= min(20, low_count * 3)
ops_score -= 20 if readiness != "READY" else 0
ops_score = max(0, ops_score)

cashflow_pd = data["cashflow"].to_pandas() if not data["cashflow"].is_empty() else pd.DataFrame()
cash_in = float(cashflow_pd.loc[cashflow_pd["Type"] == "Entrada", "total"].sum()) if not cashflow_pd.empty else 0.0
cash_out = float(cashflow_pd.loc[cashflow_pd["Type"] == "Saída", "total"].sum()) if not cashflow_pd.empty else 0.0
cash_net = cash_in - cash_out

fixed_costs, fixed_total = load_fixed_costs()
burn_ratio = (float(fixed_total) / revenue * 100) if revenue else 0.0
turnover_pd = data["turnover"].to_pandas() if not data["turnover"].is_empty() else pd.DataFrame()
avg_turnover = float(turnover_pd["giro"].mean()) if not turnover_pd.empty else 0.0
sell_through = (units / (units + inventory_pd["current_stock"].sum()) * 100) if not inventory_pd.empty and units else 0.0

_ops_conn = get_conn()
_reorder_live = pd.DataFrame()
_ops_events: list = []
_velocity_stats = pd.DataFrame()
try:
    _reorder_live = get_alerts(_ops_conn)
    _ops_events = detect_operational_events(_ops_conn, _reorder_live if not _reorder_live.empty else None)
    _velocity_stats = get_sku_velocity_stats(_ops_conn)
finally:
    _ops_conn.close()

_ai_status = "ACTIVE" if _ops_events else "WATCH"
_ai_sub = f"{len(_ops_events)} rule events" if _ops_events else "rules engine online"

terminal_header(
    [
        {"label": "Daily Revenue", "value": money(revenue, 0), "sub": "selected operating window", "color": HUD["green"]},
        {"label": "Cashflow Status", "value": money(cash_net, 0), "sub": f"in {money(cash_in, 0)} / out {money(cash_out, 0)}", "color": HUD["gold"] if cash_net >= 0 else HUD["red"]},
        {"label": "Inventory Valuation", "value": money(data["inventory_value"], 0), "sub": f"{total_skus} active SKUs", "color": HUD["cyan"]},
        {"label": "Operational Health", "value": f"{ops_score}/100", "sub": readiness, "color": HUD["green"] if ops_score >= 80 else HUD["amber"]},
        {"label": "Sync Status", "value": "SYNCED" if data["health"].get("ok") else "CHECK", "sub": _last_sync_label(), "color": status_color("ready" if data["health"].get("ok") else "warning")},
        {"label": "AI Assistant", "value": _ai_status, "sub": _ai_sub, "color": HUD["cyan"]},
    ]
)
command_tape(
    [
        "01) Inventory Matrix",
        "02) Cashflow Ops",
        "03) Sales Velocity",
        "04) Reorder Actions",
        "05) Risk Alerts",
        "06) Export Desk",
    ]
)

main_col, ai_col = st.columns([2.85, 1.15], gap="small")

with main_col:
    panel(
        "Executive KPI Cluster",
        "financial + operational control",
        kpi_grid(
            [
                {"label": "Revenue", "value": money(revenue, 0), "delta": "gross sales intelligence", "color": HUD["green"]},
                {"label": "Margin", "value": f"{margin_pct:.1f}%", "delta": money(profit, 0), "color": HUD["gold"]},
                {"label": "Inventory Turnover", "value": f"{avg_turnover:.2f}x", "delta": "sales / live stock", "color": HUD["cyan"]},
                {"label": "Sell-through", "value": f"{sell_through:.1f}%", "delta": "units sold vs available", "color": HUD["green"]},
                {"label": "Average Ticket", "value": money(ticket, 2), "delta": f"{number(units, 0)} units", "color": HUD["text"]},
                {"label": "Low Stock Alerts", "value": str(low_count), "delta": f"{critical_count} critical", "color": HUD["red"] if critical_count else HUD["amber"]},
                {"label": "Ops Efficiency", "value": f"{ops_score}/100", "delta": readiness.lower(), "color": HUD["green"] if ops_score >= 80 else HUD["amber"]},
                {"label": "Fixed Burn", "value": f"{burn_ratio:.1f}%", "delta": money(float(fixed_total), 0), "color": HUD["gold"]},
            ]
        ),
    )

    panel("Period Breakdown", "month + week control", "")
    render_executive_period_panel(data["exec_months"], data["exec_weeks"])

    grid_left, grid_mid = st.columns([1.15, 1], gap="small")

    with grid_left:
        if not inventory_pd.empty:
            stock_matrix = (
                inventory_pd.pivot_table(index="category", columns="alert", values="product", aggfunc="count", fill_value=0)
                .reset_index()
            )
            stock_matrix.columns = [str(c).replace("🔴 ", "").replace("🟡 ", "").replace("🟢 ", "") for c in stock_matrix.columns]
            fig_stock = px.imshow(
                stock_matrix.set_index("category"),
                aspect="auto",
                color_continuous_scale=[[0, "#0B1515"], [0.5, HUD["amber"]], [1, HUD["red"]]],
                labels=dict(color="SKUs"),
            )
            hud_plotly_layout(fig_stock, height=300)
            fig_stock.update_layout(margin=dict(l=8, r=8, t=18, b=8), coloraxis_showscale=False)
            panel("Inventory Intelligence", "stock health matrix", "")
            st.plotly_chart(fig_stock, use_container_width=True)

            critical_table = inventory_pd.sort_values(["alert", "current_stock"]).head(8).copy()
            critical_table = critical_table[["product", "category", "current_stock", "min_stock", "alert"]]
            critical_table.columns = ["SKU", "Category", "Stock", "Min", "State"]
            panel("Critical SKU Watchlist", "reorder + risk", dataframe_table(critical_table, 8))
        else:
            panel("Inventory Intelligence", "awaiting sync", "Run bash scripts/sync_excel.sh to rebuild read models.")

    with grid_mid:
        monthly_pd = data["monthly"].to_pandas() if not data["monthly"].is_empty() else pd.DataFrame()
        if not monthly_pd.empty:
            fig_month = go.Figure()
            fig_month.add_bar(x=monthly_pd["mes"], y=monthly_pd["receita"], name="Revenue", marker_color=HUD["green"])
            fig_month.add_scatter(x=monthly_pd["mes"], y=monthly_pd["unidades"], name="Units", yaxis="y2", line=dict(color=HUD["cyan"], width=2))
            hud_plotly_layout(fig_month, height=300)
            fig_month.update_layout(
                margin=dict(l=8, r=8, t=18, b=8),
                yaxis2=dict(overlaying="y", side="right", showgrid=False, color=HUD["cyan"]),
                legend=dict(orientation="h", y=1.08, x=0),
            )
            panel("Sales Intelligence", "velocity + demand trend", "")
            st.plotly_chart(fig_month, use_container_width=True)

        category_pd = data["category"].to_pandas() if not data["category"].is_empty() else pd.DataFrame()
        if not category_pd.empty:
            category_view = category_pd.head(8).copy()
            category_view["revenue"] = category_view["revenue"].map(lambda x: money(x, 0))
            category_view["profit"] = category_view["profit"].map(lambda x: money(x, 0))
            category_view.columns = ["Category", "Revenue", "Profit", "Units"]
            panel("Category Intelligence", "premium retail mix", dataframe_table(category_view, 8))

    lower_left, lower_right = st.columns([1, 1], gap="small")

    with lower_left:
        if not cashflow_pd.empty:
            fig_cash = px.bar(
                cashflow_pd,
                x="Category",
                y="total",
                color="Type",
                color_discrete_map={"Entrada": HUD["green"], "Saída": HUD["red"]},
                labels={"total": "R$", "Category": ""},
            )
            hud_plotly_layout(fig_cash, height=285)
            fig_cash.update_layout(margin=dict(l=8, r=8, t=18, b=40), legend=dict(orientation="h", y=1.08, x=0))
            panel("Cashflow Operations", "revenue vs expenses", "")
            st.plotly_chart(fig_cash, use_container_width=True)

    with lower_right:
        payment_pd = data["payment"].to_pandas() if not data["payment"].is_empty() else pd.DataFrame()
        if not payment_pd.empty:
            fig_pay = px.bar(
                payment_pd,
                x="Payment_Method",
                y="revenue",
                color="revenue",
                color_continuous_scale=[[0, HUD["navy"]], [1, HUD["cyan"]]],
                labels={"revenue": "R$", "Payment_Method": ""},
            )
            hud_plotly_layout(fig_pay, height=285)
            fig_pay.update_layout(margin=dict(l=8, r=8, t=18, b=40), coloraxis_showscale=False)
            panel("Payment Method Analytics", "daily commerce rails", "")
            st.plotly_chart(fig_pay, use_container_width=True)

    abc_pd = data["abc"].to_pandas() if not data["abc"].is_empty() else pd.DataFrame()
    if not abc_pd.empty:
        product_perf = abc_pd.head(12).copy()
        product_perf = product_perf[["full_name", "category", "revenue", "qty_sold", "margin_pct", "abc_class"]]
        product_perf["revenue"] = product_perf["revenue"].map(lambda x: money(x, 0))
        product_perf["margin_pct"] = product_perf["margin_pct"].map(lambda x: f"{x:.1f}%")
        product_perf.columns = ["SKU", "Category", "Revenue", "Units", "Margin", "ABC"]
        panel("Bloomberg-Style Product Tape", "top revenue drivers", dataframe_table(product_perf, 12))

    latest_pd = data["latest_sales"].to_pandas() if not data["latest_sales"].is_empty() else pd.DataFrame()
    timeline_events = read_recent_events(limit=20)
    feed_rows = events_to_feed_rows(timeline_events, severity_colors={
        "HIGH": HUD["red"],
        "CRITICAL": HUD["red"],
        "MEDIUM": HUD["amber"],
        "LOW": HUD["cyan"],
        "INFO": HUD["gold"],
    })
    if not feed_rows:
        feed_rows = [
            {"time": _last_sync_label()[-5:], "type": "SYNC", "message": "Excel master synchronized into parquet/DuckDB read models.", "color": HUD["green"]},
        ]
    if critical_count and not any("critical" in r.get("message", "").lower() for r in feed_rows):
        top_critical = inventory_pd.loc[inventory_pd["alert"] == "🔴 Crítico", "product"].head(1).to_list()
        feed_rows.insert(0, {
            "time": "RISK",
            "type": "ALERT",
            "message": f"Critical inventory exposure: {top_critical[0] if top_critical else critical_count} SKU(s).",
            "color": HUD["red"],
        })
    for row in latest_pd.head(3).itertuples(index=False):
        feed_rows.append({"time": str(row.Date)[5:], "type": "SALE", "message": f"{row.Product} | {int(row.Quantity)} un. | {money(row.Total, 2)}", "color": HUD["gold"]})
    panel("Operational Timeline", "event stream + recent sales", feed(feed_rows))

    margin_pd = data["margin"].to_pandas() if not data["margin"].is_empty() else pd.DataFrame()
    decision_rows = build_decision_map_summary(margin_pd) if not margin_pd.empty else []
    if decision_rows:
        decision_table = pd.DataFrame(decision_rows)[["velocity", "margin", "quadrant", "sku_count", "action"]]
        decision_table.columns = ["Velocity", "Margin", "Quadrant", "SKUs", "Action"]
        panel("Merchandising Decision Map", "velocity × margin → action", dataframe_table(decision_table, 4))

with ai_col:
    reorder_df = _reorder_live if _reorder_live is not None else get_alerts(get_conn())
    velocity_by_product = (
        _velocity_stats.set_index("product") if not _velocity_stats.empty else None
    )
    insights = []
    for ev in _ops_events[:4]:
        sev = str(ev.get("severity", "INFO"))
        color = HUD["red"] if sev == "HIGH" else HUD["amber"] if sev == "MEDIUM" else HUD["cyan"]
        insights.append({
            "time": "OPS",
            "type": str(ev.get("event_type", "EVENT"))[:8],
            "message": str(ev.get("message", ""))[:180],
            "color": color,
        })
    if not reorder_df.empty:
        urgent = reorder_df[reorder_df["days_remaining"] <= LEAD_TIME_DAYS].head(4)
        for row in urgent.itertuples(index=False):
            base = row._asdict() if hasattr(row, "_asdict") else dict(row._mapping)
            vrow = None
            if velocity_by_product is not None and str(base.get("product", "")) in velocity_by_product.index:
                vrow = velocity_by_product.loc[str(base["product"])]
            enriched = enrich_reorder_alert(base, vrow)
            insights.append({
                "time": "AI",
                "type": enriched.get("priority", "RESTOCK"),
                "message": enriched.get("explanation", str(row.product))[:180],
                "color": HUD["red"] if enriched.get("priority") == "HIGH" else HUD["amber"],
            })
    if margin_pct < 45 and revenue > 0 and len(insights) < 6:
        insights.append({"time": "AI", "type": "MARGIN", "message": f"Gross margin at {margin_pct:.1f}%. Review pricing on high-velocity low-margin SKUs.", "color": HUD["amber"]})
    if burn_ratio > 35 and len(insights) < 6:
        insights.append({"time": "AI", "type": "BURN", "message": f"Fixed monthly cost load is {burn_ratio:.1f}% of revenue. Monitor runway and staffing sensitivity.", "color": HUD["gold"]})
    if readiness != "READY" and len(insights) < 6:
        insights.append({"time": "AI", "type": "DATA", "message": "Production readiness is not green. Validate workbook Meta, sales, inventory, and cashflow before executive use.", "color": HUD["amber"]})
    if healthy_skus and not critical_count and len(insights) < 6:
        insights.append({"time": "AI", "type": "HEALTH", "message": "Inventory risk is contained. Use category mix and ABC velocity to prioritize restock capital.", "color": HUD["green"]})
    if not insights:
        insights.append({"time": "AI", "type": "WATCH", "message": "No material anomaly detected in the current read models.", "color": HUD["green"]})

    panel("AI Retail Insights", "explainable rule engine", feed(insights))

    risk_rows = [
        {"time": "SKU", "type": "RISK", "message": f"{critical_count} critical SKUs require immediate attention.", "color": HUD["red"] if critical_count else HUD["green"]},
        {"time": "INV", "type": "SLOW", "message": f"{int((turnover_pd['giro'] < 0.25).sum()) if not turnover_pd.empty else 0} slow-moving SKUs on overstock watch.", "color": HUD["amber"]},
        {"time": "SRC", "type": "DATA", "message": f"Reliability state: {readiness}. Source health governs executive confidence.", "color": status_color(str(health.get("readiness_state", "")))},
        {"time": "CF", "type": "CASH", "message": f"Runway signal {'OK' if cash_net >= 0 else 'NEG'} at {money(cash_net, 0)} net.", "color": HUD["green"] if cash_net >= 0 else HUD["red"]},
    ]
    panel("Operational Anomalies", "risk warnings", feed(risk_rows))

    flow_body = f"""
<div style="font-size:0.97rem;line-height:1.75;color:{HUD['text']};">
  <div><strong style="color:{HUD['gold']};">CANONICAL WRITE:</strong> data/excel/FuloFilo_Master.xlsx</div>
  <div><strong style="color:{HUD['cyan']};">SYNC PATH:</strong> bash scripts/sync_excel.sh</div>
  <div><strong style="color:{HUD['text_dim']};">READ MODELS:</strong> parquet + DuckDB + reports</div>
  <div><strong style="color:{HUD['green']};">POLICY:</strong> generated layers remain reproducible and read-only</div>
</div>
"""
    panel("System Contract", "Excel-first architecture", flow_body)

status_bar(
    [
        {"label": "Excel Sync", "value": "MASTER ONLINE" if data["health"].get("ok") else "VERIFY", "state": "ready" if data["health"].get("ok") else "warning"},
        {"label": "DuckDB", "value": "VIEW LAYER", "state": "online"},
        {"label": "Streamlit Runtime", "value": "ACTIVE", "state": "online"},
        {"label": "Last Sync", "value": _last_sync_label(), "state": "synced"},
        {"label": "Data Health", "value": readiness, "state": str(health.get("readiness_state", ""))},
        {"label": "Production Readiness", "value": "GREEN" if health.get("healthy_production_data") else "AMBER", "state": "ready" if health.get("healthy_production_data") else "warning"},
    ]
)
