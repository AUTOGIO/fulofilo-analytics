"""Product launch cohort curves (first-sale month onward)."""

from __future__ import annotations

import polars as pl


def product_launch_cohorts(conn, max_months: int = 6) -> pl.DataFrame:
    try:
        return conn.execute(f"""
            WITH first_sale AS (
                SELECT
                    COALESCE(NULLIF(s.sku, ''), p.sku) AS sku,
                    MIN(CAST(s.Date AS DATE)) AS first_date
                FROM sales s
                LEFT JOIN products p ON s.sku = p.sku OR lower(s.Product) = lower(p.full_name)
                WHERE COALESCE(NULLIF(s.sku, ''), p.sku, '') != ''
                GROUP BY 1
            ),
            monthly AS (
                SELECT
                    f.sku,
                    strftime(f.first_date, '%Y-%m') AS launch_month,
                    CAST(
                        (EXTRACT('year' FROM CAST(s.Date AS DATE)) - EXTRACT('year' FROM f.first_date)) * 12
                        + EXTRACT('month' FROM CAST(s.Date AS DATE)) - EXTRACT('month' FROM f.first_date)
                    AS INTEGER) AS months_since_launch,
                    SUM(CAST(s.Quantity AS DOUBLE)) AS units,
                    SUM(CAST(s.Total AS DOUBLE)) AS revenue
                FROM first_sale f
                JOIN sales s ON COALESCE(NULLIF(s.sku, ''), '') = f.sku
                    OR lower(s.Product) IN (
                        SELECT lower(full_name) FROM products WHERE sku = f.sku
                    )
                GROUP BY 1, 2, 3
            )
            SELECT *
            FROM monthly
            WHERE months_since_launch BETWEEN 0 AND {int(max_months)}
            ORDER BY launch_month, sku, months_since_launch
        """).pl()
    except Exception:
        return pl.DataFrame()
