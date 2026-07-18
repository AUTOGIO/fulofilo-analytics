"""Single-store segment benchmarking."""

from __future__ import annotations

import polars as pl


def category_benchmarks(conn) -> pl.DataFrame:
    try:
        return conn.execute("""
            SELECT
                p.category,
                SUM(p.revenue) AS revenue,
                SUM(p.qty_sold) AS units,
                AVG(p.margin_pct) AS avg_margin_pct,
                SUM(p.profit) AS profit,
                COUNT(*) AS sku_count,
                SUM(COALESCE(i.current_stock, 0)) AS total_stock,
                CASE
                    WHEN SUM(COALESCE(i.current_stock, 0)) > 0
                    THEN SUM(p.qty_sold)::FLOAT / SUM(COALESCE(i.current_stock, 0))
                    ELSE 0
                END AS turnover
            FROM products p
            LEFT JOIN inventory i ON p.sku = i.sku
            GROUP BY p.category
            ORDER BY revenue DESC
        """).pl()
    except Exception:
        return pl.DataFrame()


def abc_benchmarks(conn) -> pl.DataFrame:
    try:
        return conn.execute("""
            SELECT
                abc_class,
                COUNT(*) AS sku_count,
                SUM(revenue) AS revenue,
                SUM(profit) AS profit,
                AVG(margin_pct) AS avg_margin_pct,
                SUM(qty_sold) AS units
            FROM products
            GROUP BY abc_class
            ORDER BY abc_class
        """).pl()
    except Exception:
        return pl.DataFrame()
