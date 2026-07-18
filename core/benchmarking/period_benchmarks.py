"""Period-over-period benchmarking."""

from __future__ import annotations

import polars as pl

from app.db import get_executive_monthly_breakdown, get_executive_weekly_breakdown


def monthly_comparison(conn, limit: int = 6) -> pl.DataFrame:
    df = get_executive_monthly_breakdown(conn, limit=limit)
    if df.is_empty() or df.height < 2:
        return df
    df = df.sort("period_key")
    df = df.with_columns(
        pl.col("receita").pct_change().alias("revenue_mom_pct"),
        pl.col("unidades").pct_change().alias("units_mom_pct"),
        pl.col("margin_pct").diff().alias("margin_mom_pts"),
    )
    return df


def weekly_comparison(conn, limit: int = 8) -> pl.DataFrame:
    return get_executive_weekly_breakdown(conn, limit=limit)
