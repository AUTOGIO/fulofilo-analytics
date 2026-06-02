"""
FulôFiló — Executive Daily Briefing
=====================================
Composes a morning operational digest from read models (deterministic, no LLM).
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BRIEFING_JSON = ROOT / "data" / "outputs" / "daily_briefing.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _money(v: float) -> str:
    return f"R$ {int(round(v)):,}".replace(",", ".")


def generate_daily_briefing(conn) -> dict[str, Any]:
    """Build structured daily briefing from DuckDB read models."""
    from app.db import get_inventory_alerts, get_summary_kpis
    from app.utils.fixed_costs import load_fixed_costs
    from app.utils.reorder_engine import LEAD_TIME_DAYS, get_alerts
    from app.utils.source_health import get_source_health
    from core.event_engine import detect_operational_events

    kpis = get_summary_kpis(conn)
    revenue = float(kpis[0] or 0) if kpis else 0.0
    profit = float(kpis[2] or 0) if kpis else 0.0
    margin_pct = (profit / revenue * 100) if revenue else 0.0

    health_blob = get_source_health()
    health = health_blob.get("health", {}) if isinstance(health_blob, dict) else {}
    readiness = str(health.get("readiness_state", "unknown")).upper()

    inv_df = get_inventory_alerts(conn)
    critical_count = 0
    if hasattr(inv_df, "to_pandas") and not inv_df.is_empty():
        inv_pd = inv_df.to_pandas()
        critical_count = int((inv_pd.get("alert") == "🔴 Crítico").sum())

    alerts_df = get_alerts(conn)
    urgent_count = int((alerts_df["days_remaining"] <= LEAD_TIME_DAYS).sum()) if not alerts_df.empty else 0
    total_reorder = int(len(alerts_df))

    _, fixed_total = load_fixed_costs()
    burn_ratio = (float(fixed_total) / revenue * 100) if revenue else 0.0

    events = detect_operational_events(conn, alerts_df if not alerts_df.empty else None)
    high_events = [e for e in events if e.get("severity") == "HIGH"]

    issues: list[str] = []
    if urgent_count:
        issues.append(f"{urgent_count} SKUs urgent reorder (≤{LEAD_TIME_DAYS}d stock)")
    elif total_reorder:
        issues.append(f"{total_reorder} SKUs on replenishment watch")
    if critical_count:
        issues.append(f"{critical_count} SKUs at critical inventory")
    if margin_pct and margin_pct < 35:
        issues.append(f"Portfolio margin {margin_pct:.1f}% below 35% floor")
    if readiness != "READY":
        issues.append(f"Data readiness: {readiness}")
    if not issues:
        issues.append("No critical operational issues detected")

    summary_lines = [
        "Today's Critical Issues:",
        *[f"- {item}" for item in issues],
        "",
        f"Revenue base: {_money(revenue)} | Margin: {margin_pct:.1f}% | Burn: {burn_ratio:.1f}%",
        f"Replenishment: {total_reorder} alerts ({urgent_count} urgent) | High-priority events: {len(high_events)}",
    ]

    top_urgent = []
    if not alerts_df.empty:
        urgent = alerts_df[alerts_df["days_remaining"] <= LEAD_TIME_DAYS].head(5)
        for row in urgent.itertuples(index=False):
            top_urgent.append(
                {
                    "product": str(row.product),
                    "days_remaining": int(row.days_remaining),
                    "suggested_qty": int(row.suggested_qty),
                }
            )

    payload: dict[str, Any] = {
        "generated_at": _utc_now(),
        "readiness": readiness,
        "revenue": revenue,
        "margin_pct": round(margin_pct, 1),
        "burn_ratio": round(burn_ratio, 1),
        "critical_skus": critical_count,
        "total_reorder_alerts": total_reorder,
        "urgent_reorder_alerts": urgent_count,
        "high_priority_events": len(high_events),
        "critical_issues": issues,
        "top_urgent": top_urgent,
        "summary_text": "\n".join(summary_lines),
    }
    return payload


def save_daily_briefing(payload: dict[str, Any]) -> Path:
    BRIEFING_JSON.parent.mkdir(parents=True, exist_ok=True)
    tmp = BRIEFING_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(BRIEFING_JSON)
    return BRIEFING_JSON


def notify_macos_briefing(payload: dict[str, Any]) -> None:
    """Fire macOS notification with briefing headline."""
    is_cloud = bool(
        os.environ.get("STREAMLIT_SHARING_MODE") or os.environ.get("IS_STREAMLIT_CLOUD")
    )
    if is_cloud:
        return

    urgent = int(payload.get("urgent_reorder_alerts") or 0)
    critical = int(payload.get("critical_skus") or 0)
    margin = float(payload.get("margin_pct") or 0)

    title = "FulôFiló — Briefing Operacional"
    if urgent:
        subtitle = f"{urgent} reposição(ões) urgente(s)"
    elif critical:
        subtitle = f"{critical} SKU(s) crítico(s)"
    else:
        subtitle = "Operação estável"

    body = f"Margem {margin:.1f}% | {payload.get('total_reorder_alerts', 0)} alertas reposição"
    script = (
        f'display notification "{body}" '
        f'with title "{title}" '
        f'subtitle "{subtitle}"'
    )
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
    except Exception:
        pass
