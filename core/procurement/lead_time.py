"""
Per-SKU lead-time optimization and reorder quantities.

Velocity-based suggested_qty is the canonical PO quantity signal.
Min-stock alerts remain a separate shelf-minimum signal in app.db.
"""

from __future__ import annotations

import math

import pandas as pd

SALES_PERIOD_DAYS = 61
ROLLING_VELOCITY_DAYS = 14
DEFAULT_LEAD_TIME_DAYS = 12
DEFAULT_BUFFER_DAYS = 12
COVERAGE_DAYS = 45

_Z_BY_ABC = {"A": 1.65, "B": 1.28, "C": 1.0}


def _z_score(abc_class: str) -> float:
    return _Z_BY_ABC.get(str(abc_class or "C").upper(), 1.0)


def _demand_std(conn) -> pd.DataFrame:
    """Per-SKU std dev of daily demand over the last 28 sale days."""
    try:
        return conn.execute(f"""
            WITH ref AS (
                SELECT MAX(CAST(Date AS DATE)) AS max_date FROM sales
            ),
            daily AS (
                SELECT
                    COALESCE(NULLIF(s.sku, ''), p.sku) AS sku,
                    CAST(s.Date AS DATE) AS sale_date,
                    SUM(CAST(s.Quantity AS DOUBLE)) AS qty
                FROM sales s
                LEFT JOIN products p ON lower(s.Product) = lower(p.full_name)
                CROSS JOIN ref r
                WHERE CAST(s.Date AS DATE) > r.max_date - INTERVAL 28 DAY
                GROUP BY 1, 2
            )
            SELECT sku, STDDEV_SAMP(qty) AS demand_std
            FROM daily
            WHERE sku IS NOT NULL AND sku != ''
            GROUP BY sku
        """).df()
    except Exception:
        return pd.DataFrame(columns=["sku", "demand_std"])


def get_reorder_df(conn) -> pd.DataFrame:
    """Full reorder analysis with per-SKU lead time and dynamic safety buffer."""
    try:
        df = conn.execute(f"""
            WITH ref AS (
                SELECT MAX(CAST(Date AS DATE)) AS max_date FROM sales
            ),
            rolling AS (
                SELECT
                    COALESCE(NULLIF(s.sku, ''), p.sku) AS sku,
                    s.Product AS product,
                    SUM(CASE
                        WHEN CAST(s.Date AS DATE) > r.max_date - INTERVAL {ROLLING_VELOCITY_DAYS} DAY
                        THEN CAST(s.Quantity AS DOUBLE) ELSE 0 END) AS qty_14d
                FROM sales s
                LEFT JOIN products p ON lower(s.Product) = lower(p.full_name)
                CROSS JOIN ref r
                GROUP BY 1, 2
            )
            SELECT
                p.sku                                                                AS slug,
                p.sku                                                                AS sku,
                p.full_name                                                          AS product,
                p.category,
                p.abc_class,
                p.unit_cost,
                COALESCE(i.current_stock, 0)                                         AS current_stock,
                CASE WHEN COALESCE(i.current_stock, 0) = 0 THEN TRUE ELSE FALSE END AS stock_unknown,
                p.qty_sold,
                p.margin_pct,
                p.unit_profit,
                COALESCE(i.supplier, '')                                             AS supplier,
                COALESCE(ro.qty_14d, 0)                                              AS qty_14d,
                ROUND(
                    CASE
                        WHEN COALESCE(ro.qty_14d, 0) > 0
                        THEN ro.qty_14d::FLOAT / {ROLLING_VELOCITY_DAYS}
                        ELSE p.qty_sold::FLOAT / {SALES_PERIOD_DAYS}
                    END
                , 4)                                                                 AS daily_rate,
                COALESCE(
                    NULLIF(CAST(i.lead_time_days AS INTEGER), 0),
                    NULLIF(CAST(sc.lead_time_days AS INTEGER), 0),
                    {DEFAULT_LEAD_TIME_DAYS}
                )                                                                    AS lead_time,
                COALESCE(sc.supplier_id, '')                                         AS supplier_id,
                COALESCE(sc.supplier_name, i.supplier, 'Não atribuído')            AS supplier_name,
                COALESCE(NULLIF(CAST(sc.moq AS INTEGER), 0), 0)                      AS moq,
                COALESCE(NULLIF(CAST(sc.case_pack AS INTEGER), 0), 1)              AS case_pack
            FROM products p
            LEFT JOIN inventory i ON p.sku = i.sku
            LEFT JOIN rolling ro ON p.sku = ro.sku
            LEFT JOIN supplier_catalog sc ON p.sku = sc.sku
            WHERE p.qty_sold > 0 OR COALESCE(ro.qty_14d, 0) > 0
            ORDER BY p.full_name
        """).df()
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return df

    std_df = _demand_std(conn)
    if not std_df.empty:
        df = df.merge(std_df, on="sku", how="left")
    else:
        df["demand_std"] = 0.0

    df["demand_std"] = df["demand_std"].fillna(0.0)
    df["buffer"] = df.apply(
        lambda r: max(
            DEFAULT_BUFFER_DAYS,
            math.ceil(
                _z_score(r.get("abc_class", "C"))
                * float(r.get("demand_std") or 0)
                * math.sqrt(max(float(r.get("lead_time") or DEFAULT_LEAD_TIME_DAYS), 1))
            ),
        ),
        axis=1,
    )
    df["alert_threshold"] = df["lead_time"] + df["buffer"]

    rate = df["daily_rate"].astype(float)
    stock = df["current_stock"].astype(float)
    df["days_remaining"] = (stock / rate.replace(0, float("nan"))).round(0).fillna(9999)
    need = (rate * COVERAGE_DAYS - stock).clip(lower=0)
    df["suggested_qty"] = need.apply(math.ceil).astype(int)

    # Round to case_pack and enforce MOQ
    def _round_qty(row) -> int:
        qty = int(row["suggested_qty"])
        pack = max(int(row.get("case_pack") or 1), 1)
        moq = int(row.get("moq") or 0)
        if qty <= 0:
            return 0
        if pack > 1:
            qty = int(math.ceil(qty / pack) * pack)
        if moq > 0 and qty < moq:
            qty = moq
        return qty

    df["suggested_qty"] = df.apply(_round_qty, axis=1)
    return df.sort_values("days_remaining", ascending=True, na_position="last").reset_index(drop=True)


def get_alerts(conn) -> pd.DataFrame:
    """Products where days_remaining is at or below the dynamic alert threshold."""
    df = get_reorder_df(conn)
    if df.empty:
        return df
    mask = df["days_remaining"] <= df["alert_threshold"]
    return df[mask].reset_index(drop=True)


def urgency_label(days: float, lead_time: float = DEFAULT_LEAD_TIME_DAYS) -> str:
    if days <= lead_time:
        return "🔴 URGENTE"
    return "🟡 ATENÇÃO"
