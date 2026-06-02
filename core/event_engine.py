"""
FulôFiló — Operational Event Engine
===================================
Deterministic rules for velocity spikes, stockout risk, and margin compression.
GPT/LLM is not used — rules fire first; ambiguity can be layered later.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from core.classification import FIXED_MARGIN_THRESHOLD
from core.ops_events import emit_event

# ── Rule thresholds ───────────────────────────────────────────────────────────
VELOCITY_SPIKE_RATIO = 2.4          # 7d rate / 21d baseline rate
STOCKOUT_DAYS_HIGH = 5              # days remaining for HIGH priority
HIGH_PRIORITY_MARGIN_MIN = FIXED_MARGIN_THRESHOLD
ROLLING_VELOCITY_DAYS = 14
BASELINE_VELOCITY_DAYS = 21         # prior window for spike detection
RECENT_VELOCITY_DAYS = 7


def get_sku_velocity_stats(conn) -> pd.DataFrame:
    """
    Per-SKU velocity metrics from daily_sales.
    Returns empty DataFrame if sales view is unavailable.
    """
    try:
        return conn.execute(f"""
            WITH ref AS (
                SELECT MAX(CAST(Date AS DATE)) AS max_date FROM sales
            ),
            agg AS (
                SELECT
                    s.Product AS product,
                    SUM(CASE
                        WHEN CAST(s.Date AS DATE) > r.max_date - INTERVAL {RECENT_VELOCITY_DAYS} DAY
                        THEN CAST(s.Quantity AS DOUBLE) ELSE 0 END) AS qty_7d,
                    SUM(CASE
                        WHEN CAST(s.Date AS DATE) > r.max_date - INTERVAL {RECENT_VELOCITY_DAYS + BASELINE_VELOCITY_DAYS} DAY
                         AND CAST(s.Date AS DATE) <= r.max_date - INTERVAL {RECENT_VELOCITY_DAYS} DAY
                        THEN CAST(s.Quantity AS DOUBLE) ELSE 0 END) AS qty_21d,
                    SUM(CASE
                        WHEN CAST(s.Date AS DATE) > r.max_date - INTERVAL {ROLLING_VELOCITY_DAYS} DAY
                        THEN CAST(s.Quantity AS DOUBLE) ELSE 0 END) AS qty_14d
                FROM sales s
                CROSS JOIN ref r
                GROUP BY s.Product
            )
            SELECT
                product,
                qty_7d,
                qty_21d,
                qty_14d,
                ROUND(qty_7d / {RECENT_VELOCITY_DAYS}.0, 3) AS daily_rate_7d,
                ROUND(qty_14d / {ROLLING_VELOCITY_DAYS}.0, 3) AS daily_rate_14d,
                ROUND(qty_21d / {BASELINE_VELOCITY_DAYS}.0, 3) AS daily_rate_21d_baseline,
                CASE
                    WHEN qty_21d > 0 THEN ROUND((qty_7d / {RECENT_VELOCITY_DAYS}.0) /
                         (qty_21d / {BASELINE_VELOCITY_DAYS}.0), 2)
                    ELSE NULL
                END AS velocity_ratio
            FROM agg
            WHERE qty_7d > 0 OR qty_14d > 0
        """).df()
    except Exception:
        return pd.DataFrame()


def _confidence_from_signals(met: int, total: int = 3) -> str:
    if met >= total:
        return "HIGH"
    if met >= 2:
        return "MEDIUM"
    return "LOW"


def enrich_reorder_alert(row: dict[str, Any], velocity_row: pd.Series | None) -> dict[str, Any]:
    """
    Add explainability fields to a reorder alert record.
    """
    days_remaining = float(row.get("days_remaining") or 0)
    daily_rate = float(row.get("daily_rate") or 0)
    margin_pct = float(row.get("margin_pct") or 0)
    unit_profit = float(row.get("unit_profit") or 0)
    lead_time = float(row.get("lead_time") or 12)
    current_stock = float(row.get("current_stock") or 0)
    suggested_qty = int(row.get("suggested_qty") or 0)

    velocity_ratio = None
    velocity_change_pct = None
    if velocity_row is not None and not pd.isna(velocity_row.get("velocity_ratio")):
        velocity_ratio = float(velocity_row["velocity_ratio"])
        velocity_change_pct = round((velocity_ratio - 1) * 100, 1)

    signals: dict[str, Any] = {
        "days_remaining": round(days_remaining, 1),
        "daily_rate": round(daily_rate, 3),
        "current_stock": int(current_stock),
        "lead_time_days": int(lead_time),
        "margin_pct": round(margin_pct, 1),
        "suggested_qty": suggested_qty,
    }
    if velocity_ratio is not None:
        signals["velocity_ratio"] = velocity_ratio
        signals["velocity_change_pct"] = velocity_change_pct
        signals["daily_rate_14d"] = float(velocity_row.get("daily_rate_14d") or 0)

    thresholds_met = 0
    if days_remaining <= STOCKOUT_DAYS_HIGH:
        thresholds_met += 1
    if velocity_ratio is not None and velocity_ratio >= VELOCITY_SPIKE_RATIO:
        thresholds_met += 1
    if margin_pct >= HIGH_PRIORITY_MARGIN_MIN:
        thresholds_met += 1

    if thresholds_met >= 3:
        priority = "HIGH"
        action = "HIGH_PRIORITY_REPLENISHMENT"
    elif days_remaining <= lead_time:
        priority = "HIGH"
        action = "REPLENISH"
    elif days_remaining <= float(row.get("alert_threshold") or 24):
        priority = "MEDIUM"
        action = "REPLENISH"
    else:
        priority = "LOW"
        action = "MONITOR"

    days_at_risk = max(0.0, lead_time - days_remaining)
    projected_lost_profit = round(daily_rate * unit_profit * days_at_risk, 2)

    confidence = _confidence_from_signals(thresholds_met)

    why_parts = [f"{int(days_remaining)} days stock remaining"]
    if velocity_change_pct is not None:
        sign = "+" if velocity_change_pct >= 0 else ""
        why_parts.append(f"velocity {sign}{velocity_change_pct}% (7d vs 21d baseline)")
    why_parts.append(f"lead time {int(lead_time)}d")
    if margin_pct:
        why_parts.append(f"margin {margin_pct:.1f}%")

    explanation = (
        f"REORDER — {row.get('product', 'SKU')}: "
        + "; ".join(why_parts)
        + (f". Projected lost profit ~R$ {projected_lost_profit:,.2f}" if projected_lost_profit else "")
        + f". Confidence: {confidence}."
    )

    enriched = dict(row)
    enriched.update(
        {
            "priority": priority,
            "action": action,
            "confidence": confidence,
            "signals": signals,
            "projected_impact": {
                "projected_lost_profit_brl": projected_lost_profit,
                "days_at_risk": round(days_at_risk, 1),
            },
            "explanation": explanation,
            "thresholds_met": thresholds_met,
        }
    )
    return enriched


def detect_operational_events(conn, reorder_df: pd.DataFrame | None = None) -> list[dict[str, Any]]:
    """
    Scan read models and return structured operational events (does not persist).
    """
    from app.utils.reorder_engine import ALERT_THRESHOLD, get_reorder_df

    events: list[dict[str, Any]] = []
    velocity_df = get_sku_velocity_stats(conn)
    velocity_by_product = (
        velocity_df.set_index("product") if not velocity_df.empty else pd.DataFrame()
    )

    if reorder_df is None:
        reorder_df = get_reorder_df(conn)

    if reorder_df.empty:
        return events

    alerts = reorder_df[reorder_df["days_remaining"] <= ALERT_THRESHOLD]
    for row in alerts.itertuples(index=False):
        product = str(row.product)
        vrow = None
        if not velocity_by_product.empty and product in velocity_by_product.index:
            vrow = velocity_by_product.loc[product]

        base = row._asdict() if hasattr(row, "_asdict") else dict(row._mapping)
        enriched = enrich_reorder_alert(base, vrow)

        if enriched["priority"] == "HIGH" and enriched.get("thresholds_met", 0) >= 2:
            events.append(
                {
                    "event_type": "REORDER",
                    "severity": "HIGH",
                    "product": product,
                    "sku": str(base.get("slug", "")),
                    "action": enriched["action"],
                    "message": enriched["explanation"],
                    "signals": enriched["signals"],
                }
            )

    # Margin compression: portfolio margin below floor with high-velocity SKUs
    try:
        margin_row = conn.execute("""
            SELECT
                ROUND(SUM(revenue * margin_pct / 100) / NULLIF(SUM(revenue), 0) * 100, 1) AS portfolio_margin
            FROM products WHERE revenue > 0
        """).fetchone()
        portfolio_margin = float(margin_row[0] or 0) if margin_row else 0.0
        if portfolio_margin > 0 and portfolio_margin < HIGH_PRIORITY_MARGIN_MIN:
            events.append(
                {
                    "event_type": "MARGIN",
                    "severity": "MEDIUM",
                    "action": "REVIEW_PRICING",
                    "message": (
                        f"Margin compression: portfolio gross margin at {portfolio_margin:.1f}% "
                        f"(floor {HIGH_PRIORITY_MARGIN_MIN:.0f}%). Review high-velocity low-margin SKUs."
                    ),
                    "signals": {"portfolio_margin_pct": portfolio_margin},
                }
            )
    except Exception:
        pass

    # Velocity spike without immediate stockout
    if not velocity_df.empty:
        spikes = velocity_df[
            (velocity_df["velocity_ratio"].notna())
            & (velocity_df["velocity_ratio"] >= VELOCITY_SPIKE_RATIO)
        ]
        alert_products = set(alerts["product"].astype(str).tolist()) if not alerts.empty else set()
        for _, v in spikes.head(5).iterrows():
            product = str(v["product"])
            if product in alert_products:
                continue
            pct = round((float(v["velocity_ratio"]) - 1) * 100, 0)
            events.append(
                {
                    "event_type": "VELOCITY",
                    "severity": "MEDIUM",
                    "product": product,
                    "action": "MONITOR_DEMAND",
                    "message": f"SKU velocity spike: {product} +{pct:.0f}% vs 21d baseline.",
                    "signals": {
                        "velocity_ratio": float(v["velocity_ratio"]),
                        "daily_rate_7d": float(v["daily_rate_7d"]),
                    },
                }
            )

    return events


def get_category_demand_forecast(conn, horizon_days: int = 7) -> list[dict[str, Any]]:
    """
    Simple 7-day category demand forecast using rolling daily rate × horizon.
    """
    try:
        df = conn.execute(f"""
            WITH ref AS (
                SELECT MAX(CAST(Date AS DATE)) AS max_date FROM sales
            ),
            daily AS (
                SELECT
                    p.category,
                    SUM(CASE
                        WHEN CAST(s.Date AS DATE) > r.max_date - INTERVAL {ROLLING_VELOCITY_DAYS} DAY
                        THEN CAST(s.Quantity AS DOUBLE) ELSE 0 END) / {ROLLING_VELOCITY_DAYS}.0 AS daily_units
                FROM sales s
                JOIN products p ON lower(s.Product) = lower(p.full_name)
                CROSS JOIN ref r
                GROUP BY p.category
            )
            SELECT
                category,
                ROUND(daily_units, 2) AS daily_units,
                ROUND(daily_units * {horizon_days}, 0) AS forecast_units_{horizon_days}d
            FROM daily
            WHERE daily_units > 0
            ORDER BY forecast_units_{horizon_days}d DESC
        """).df()
        if df.empty:
            return []
        key = f"forecast_units_{horizon_days}d"
        return [
            {
                "category": str(row.category),
                "daily_units": float(row.daily_units),
                "forecast_units": float(getattr(row, key)),
                "horizon_days": horizon_days,
            }
            for row in df.itertuples(index=False)
        ]
    except Exception:
        return []


def persist_detected_events(events: list[dict[str, Any]], *, source: str = "event_engine") -> int:
    """Write detected events to ops_events.jsonl."""
    count = 0
    for ev in events:
        emit_event(
            str(ev.get("event_type", "EVENT")),
            severity=str(ev.get("severity", "INFO")),
            message=str(ev.get("message", "")),
            sku=ev.get("sku"),
            product=ev.get("product"),
            action=ev.get("action"),
            signals=ev.get("signals"),
            source=source,
        )
        count += 1
    return count
