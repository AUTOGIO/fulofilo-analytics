"""Tourist-season and calendar cohort analysis."""

from __future__ import annotations

import polars as pl


def season_category_matrix(conn) -> pl.DataFrame:
    try:
        return conn.execute("""
            SELECT
                CAST(strftime(CAST(s.Date AS DATE), '%m') AS INTEGER) AS month_num,
                p.category,
                SUM(CAST(s.Quantity AS DOUBLE)) AS units,
                SUM(CAST(s.Total AS DOUBLE)) AS revenue
            FROM sales s
            JOIN products p ON s.sku = p.sku OR lower(s.Product) = lower(p.full_name)
            GROUP BY 1, 2
            ORDER BY month_num, revenue DESC
        """).pl()
    except Exception:
        return pl.DataFrame()
