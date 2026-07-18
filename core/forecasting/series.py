"""Build consistent sales time series from DuckDB read models."""

from __future__ import annotations

from typing import Literal

import polars as pl


def build_category_series(conn, grain: Literal["day", "week", "month"] = "day") -> pl.DataFrame:
    ts = _grain_expr(grain)
    try:
        return conn.execute(f"""
            SELECT
                {ts} AS period,
                p.category AS entity,
                'category' AS entity_type,
                SUM(CAST(s.Quantity AS DOUBLE)) AS units,
                SUM(CAST(s.Total AS DOUBLE)) AS revenue
            FROM sales s
            JOIN products p ON s.sku = p.sku OR lower(s.Product) = lower(p.full_name)
            GROUP BY 1, 2
            ORDER BY period, entity
        """).pl()
    except Exception:
        return pl.DataFrame()


def build_sku_series(conn, skus: list[str] | None = None, grain: Literal["day", "week", "month"] = "day") -> pl.DataFrame:
    ts = _grain_expr(grain)
    sku_filter = ""
    if skus:
        quoted = ", ".join(f"'{s}'" for s in skus)
        sku_filter = f"AND p.sku IN ({quoted})"
    try:
        return conn.execute(f"""
            SELECT
                {ts} AS period,
                p.sku AS entity,
                'sku' AS entity_type,
                SUM(CAST(s.Quantity AS DOUBLE)) AS units,
                SUM(CAST(s.Total AS DOUBLE)) AS revenue
            FROM sales s
            JOIN products p ON s.sku = p.sku OR lower(s.Product) = lower(p.full_name)
            WHERE 1=1 {sku_filter}
            GROUP BY 1, 2
            ORDER BY period, entity
        """).pl()
    except Exception:
        return pl.DataFrame()


def _grain_expr(grain: str) -> str:
    if grain == "week":
        return "strftime(CAST(s.Date AS DATE), '%G-W%V')"
    if grain == "month":
        return "strftime(CAST(s.Date AS DATE), '%Y-%m')"
    return "CAST(s.Date AS DATE)"
