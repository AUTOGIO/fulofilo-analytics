"""Payment channel benchmarking."""

from __future__ import annotations

import polars as pl


def channel_benchmarks(conn) -> pl.DataFrame:
    try:
        return conn.execute("""
            SELECT
                COALESCE(NULLIF(Payment_Method, ''), 'Não informado') AS payment_method,
                SUM(CAST(Total AS DOUBLE)) AS revenue,
                SUM(CAST(Quantity AS DOUBLE)) AS units,
                COUNT(*) AS transactions,
                ROUND(SUM(CAST(Total AS DOUBLE)) / NULLIF(COUNT(*), 0), 2) AS avg_ticket
            FROM sales
            GROUP BY 1
            ORDER BY revenue DESC
        """).pl()
    except Exception:
        return pl.DataFrame()


def weekday_vs_weekend(conn) -> pl.DataFrame:
    try:
        return conn.execute("""
            SELECT
                CASE
                    WHEN EXTRACT('dow' FROM CAST(Date AS DATE)) IN (0, 6) THEN 'weekend'
                    ELSE 'weekday'
                END AS day_type,
                SUM(CAST(Total AS DOUBLE)) AS revenue,
                SUM(CAST(Quantity AS DOUBLE)) AS units,
                COUNT(*) AS transactions
            FROM sales
            GROUP BY 1
        """).pl()
    except Exception:
        return pl.DataFrame()
