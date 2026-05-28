#!/usr/bin/env python3
"""
Read-model snapshot for the native SwiftUI terminal.

Goal: match the Streamlit dashboard (app/app.py) calculations as closely as possible
by reusing the same DuckDB query helpers in app/db.py and the same KPI logic.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def repo_root() -> Path:
    env = os.environ.get("FULO_REPO_ROOT")
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def money_br(v: float) -> str:
    iv = int(round(v))
    s = f"{iv:,}".replace(",", "_").replace("_", ".")
    return f"R$ {s}"


def iso_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _f(value: object) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _last_sync_label(root: Path) -> str:
    # Mirrors app/app.py:_last_sync_label shape (best-effort).
    candidates = [
        root / "app" / "utils" / "source_health.py",
        root / "data" / "parquet" / "products.parquet",
        root / "data" / "parquet" / "daily_sales.parquet",
        root / "data" / "parquet" / "inventory.parquet",
        root / "data" / "parquet" / "cashflow.parquet",
    ]
    mtimes = [p.stat().st_mtime for p in candidates if p.exists()]
    if not mtimes:
        return "never"
    return datetime.fromtimestamp(max(mtimes)).strftime("%Y-%m-%d %H:%M")


def main() -> int:
    root = repo_root()
    sys.path.insert(0, str(root))

    try:
        from app.db import (  # type: ignore
            get_abc_analysis,
            get_available_months,
            get_cashflow_summary,
            get_conn,
            get_daily_sales_trend,
            get_data_mtime,
            get_inventory_alerts,
            get_margin_matrix,
            get_monthly_breakdown,
            get_stock_turnover,
            get_summary_kpis,
        )
        from app.utils.fixed_costs import load_fixed_costs  # type: ignore
        from app.utils.source_health import get_source_health  # type: ignore
    except Exception as e:
        sys.stderr.write(f"import failed: {e}\n")
        return 2

    conn = get_conn()

    kpis = get_summary_kpis(conn)
    margin_df = get_margin_matrix(conn)
    inventory_df = get_inventory_alerts(conn)
    turnover_df = get_stock_turnover(conn)
    cashflow_df = get_cashflow_summary(conn)
    sales_trend_df = get_daily_sales_trend(conn, top_n=8)
    _ = get_abc_analysis(conn)  # parity: keep warm (not used in Swift UI yet)
    _ = get_available_months(conn)
    _ = get_monthly_breakdown(conn, [])

    try:
        inventory_value = conn.execute(
            """
            SELECT SUM(CAST(i.current_stock AS DOUBLE) * COALESCE(p.unit_cost, 0)) AS inventory_value
            FROM inventory i
            LEFT JOIN products p ON lower(i.product) = lower(p.full_name)
            """
        ).fetchone()[0]
    except Exception:
        inventory_value = 0.0

    health_blob = get_source_health()
    health = health_blob.get("health", {}) if isinstance(health_blob, dict) else {}
    readiness = str(health.get("readiness_state", "unknown")).upper()
    ok = bool(health_blob.get("ok")) if isinstance(health_blob, dict) else False

    revenue = _f(kpis[0]) if kpis else 0.0
    units = _f(kpis[1]) if kpis else 0.0
    profit = _f(kpis[2]) if kpis else 0.0
    ticket = _f(kpis[3]) if kpis else 0.0
    margin_pct = (profit / revenue * 100) if revenue else 0.0

    inv_pd = inventory_df.to_pandas() if hasattr(inventory_df, "to_pandas") and not inventory_df.is_empty() else None
    if inv_pd is not None and not inv_pd.empty:
        critical_count = int((inv_pd.get("alert") == "🔴 Crítico").sum())
        low_count = int((inv_pd.get("alert") == "🟡 Baixo").sum())
        total_skus = int(len(inv_pd))
        healthy_skus = int((inv_pd.get("alert") == "🟢 OK").sum())
        current_stock_sum = float(inv_pd["current_stock"].sum())
    else:
        critical_count = low_count = total_skus = healthy_skus = 0
        current_stock_sum = 0.0

    ops_score = 100
    ops_score -= min(35, critical_count * 7)
    ops_score -= min(20, low_count * 3)
    ops_score -= 20 if readiness != "READY" else 0
    ops_score = max(0, ops_score)

    cf_pd = cashflow_df.to_pandas() if hasattr(cashflow_df, "to_pandas") and not cashflow_df.is_empty() else None
    if cf_pd is not None and not cf_pd.empty:
        cash_in = float(cf_pd.loc[cf_pd["Type"] == "Entrada", "total"].sum())
        cash_out = float(cf_pd.loc[cf_pd["Type"] == "Saída", "total"].sum())
    else:
        cash_in = cash_out = 0.0
    cash_net = cash_in - cash_out

    _, fixed_total = load_fixed_costs()
    burn_ratio = (float(fixed_total) / revenue * 100) if revenue else 0.0

    turnover_pd = turnover_df.to_pandas() if hasattr(turnover_df, "to_pandas") and not turnover_df.is_empty() else None
    avg_turnover = float(turnover_pd["giro"].mean()) if turnover_pd is not None and not turnover_pd.empty else 0.0
    sell_through = (units / (units + current_stock_sum) * 100) if units and (units + current_stock_sum) else 0.0

    inventory_matrix = []
    if inv_pd is not None and not inv_pd.empty:
        grp = inv_pd.copy()
        grp["category"] = grp["category"].fillna("Sem categoria")
        for cat, g in grp.groupby("category"):
            total = float(len(g)) or 1.0
            inventory_matrix.append(
                {
                    "name": str(cat),
                    "healthy": float((g["alert"] == "🟢 OK").sum()) / total,
                    "watch": float((g["alert"] == "🟡 Baixo").sum()) / total,
                    "risk": float((g["alert"] == "🔴 Crítico").sum()) / total,
                }
            )

    sales_series = []
    try:
        st_pd = sales_trend_df.to_pandas() if hasattr(sales_trend_df, "to_pandas") and not sales_trend_df.is_empty() else None
        if st_pd is not None and not st_pd.empty:
            day = st_pd.groupby("Date", as_index=False)["revenue"].sum().sort_values("Date")
            tail = day.tail(6)
            for _, r in tail.iterrows():
                sales_series.append({"label": str(r["Date"]), "revenue": float(r["revenue"]), "units": 0.0})
    except Exception:
        sales_series = []

    bubbles = []
    try:
        mm_pd = margin_df.to_pandas() if hasattr(margin_df, "to_pandas") and not margin_df.is_empty() else None
        if mm_pd is not None and not mm_pd.empty:
            mm_pd = mm_pd.sort_values("revenue", ascending=False).head(120)
            for _, r in mm_pd.iterrows():
                bubbles.append(
                    {
                        "sku": str(r.get("full_name", "")),
                        "category": str(r.get("category", "Sem categoria") or "Sem categoria"),
                        "volume": float(r.get("qty_sold", 0) or 0),
                        "margin": float(r.get("margin_pct", 0) or 0),
                        "revenue": float(r.get("revenue", 0) or 0),
                    }
                )
    except Exception:
        bubbles = []

    insights = []
    try:
        if inv_pd is not None and not inv_pd.empty:
            crit = inv_pd[inv_pd["alert"] == "🔴 Crítico"].copy()
            low = inv_pd[inv_pd["alert"] == "🟡 Baixo"].copy()
            watch = list(crit.sort_values(["current_stock"], ascending=True).head(6).to_dict(orient="records"))
            watch += list(low.sort_values(["current_stock"], ascending=True).head(6).to_dict(orient="records"))
            for r in watch:
                product = str(r.get("product", ""))
                reorder = int(r.get("reorder_qty") or 0)
                insights.append(
                    {
                        "code": "RESTOC",
                        "text": product,
                        "detail": f"Stock {int(r.get('current_stock') or 0)} / min {int(r.get('min_stock') or 0)}. Suggested buy {reorder} units.",
                        "accent": "red" if r.get("alert") == "🔴 Crítico" else "amber",
                    }
                )
    except Exception:
        insights = []

    anomalies = [
        {"code": "SKU", "kind": "RISK", "text": f"{critical_count} critical SKUs require immediate attention.", "accent": "red" if critical_count else "green"},
        {"code": "INV", "kind": "LOW", "text": f"{low_count} low stock SKUs on watch.", "accent": "amber" if low_count else "green"},
        {"code": "SRC", "kind": "DATA", "text": f"Reliability state: {readiness}. Source health governs executive confidence.", "accent": "green" if readiness == "READY" else "amber"},
        {"code": "CF", "kind": "CASH", "text": f"Runway signal {'NEG' if cash_net < 0 else 'POS'} at {money_br(cash_net)} net.", "accent": "red" if cash_net < 0 else "green"},
    ]

    contract_rows = [
        {"k": "CANONICAL WRITE", "v": "data/excel/FuloFilo_Master.xlsx"},
        {"k": "SYNC PATH", "v": "bash scripts/sync_excel.sh"},
        {"k": "READ MODELS", "v": "parquet + DuckDB + reports"},
        {"k": "POLICY", "v": "generated layers remain reproducible and read-only"},
    ]

    out = {
        "meta": {
            "generated_at": iso_now(),
            "data_version": get_data_mtime(),
            "last_sync_label": _last_sync_label(root),
            "ok": ok,
        },
        "executive": {
            "revenue_fmt": money_br(revenue),
            "margin_pct": float(margin_pct),
            "profit_fmt": money_br(profit),
            "avg_ticket_fmt": money_br(ticket),
            "units": float(units),
            "cash_net_fmt": money_br(cash_net),
            "cash_in": float(cash_in),
            "cash_out": float(cash_out),
            "inv_value_fmt": money_br(_f(inventory_value)),
            "active_skus": int(total_skus),
            "low_critical": int(critical_count),
            "low_warn": int(low_count),
            "ops_score": int(ops_score),
            "readiness": readiness,
            "avg_turnover": float(avg_turnover),
            "sell_through": float(sell_through),
            "burn_ratio": float(burn_ratio),
            "fixed_total": float(fixed_total),
            "healthy_skus": int(healthy_skus),
        },
        "inventory_matrix": inventory_matrix,
        "sales_series": sales_series,
        "bubbles": bubbles,
        "insights": insights,
        "anomalies": anomalies,
        "contract": contract_rows,
    }

    conn.close()
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
