"""
FulôFiló — Category-Level Analytics (Phase 2)
===============================================
Aggregates product-level data to category summaries.
Kept strictly separate from Phase 1 classification logic.

Aggregation output per category
--------------------------------
  - avg_margin_pct   : mean margin across products in category
  - total_revenue    : sum of revenue
  - total_qty_sold   : sum of quantity sold
  - product_count    : number of products
  - star_count       : count of Stars (requires 'classification' column)
  - dog_count        : count of Dogs  (requires 'classification' column)

Public API
----------
aggregate_by_category(df) → pd.DataFrame
    Input:  product-level DataFrame (with or without 'classification')
    Output: category-level summary DataFrame, sorted by total_revenue desc.
"""

from __future__ import annotations

import logging

import pandas as pd

from core.classification import STAR, DOG

logger = logging.getLogger(__name__)

_REQUIRED = {"category", "revenue", "margin_pct", "qty_sold"}


def aggregate_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate product-level data to category summaries.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain: category, revenue, margin_pct, qty_sold.
        Optional: classification (enables star_count, dog_count columns).

    Returns
    -------
    pd.DataFrame with one row per category, sorted by total_revenue desc.
    Returns empty DataFrame (with correct columns) if input is empty or missing required columns.
    """
    missing = _REQUIRED - set(df.columns)
    if missing:
        logger.warning("aggregate_by_category: missing columns %s — returning empty.", missing)
        return pd.DataFrame(columns=[
            "category", "avg_margin_pct", "total_revenue",
            "total_qty_sold", "product_count"
        ])

    if df.empty:
        logger.warning("aggregate_by_category: empty DataFrame — returning empty.")
        return pd.DataFrame(columns=[
            "category", "avg_margin_pct", "total_revenue",
            "total_qty_sold", "product_count"
        ])

    # ── Core aggregations ──────────────────────────────────────────────────────
    agg = df.groupby("category", as_index=False).agg(
        avg_margin_pct=("margin_pct", "mean"),
        total_revenue=("revenue",    "sum"),
        total_qty_sold=("qty_sold",  "sum"),
        product_count=("category",   "count"),
    )

    # ── Classification-based counts (optional) ─────────────────────────────────
    if "classification" in df.columns:
        star_counts = (
            df[df["classification"] == STAR]
            .groupby("category")["classification"]
            .count()
            .rename("star_count")
        )
        dog_counts = (
            df[df["classification"] == DOG]
            .groupby("category")["classification"]
            .count()
            .rename("dog_count")
        )
        agg = agg.merge(star_counts, on="category", how="left")
        agg = agg.merge(dog_counts,  on="category", how="left")
        agg["star_count"] = agg["star_count"].fillna(0).astype(int)
        agg["dog_count"]  = agg["dog_count"].fillna(0).astype(int)
    else:
        logger.info("aggregate_by_category: 'classification' not present — star/dog counts skipped.")

    # ── Format ─────────────────────────────────────────────────────────────────
    agg["avg_margin_pct"] = agg["avg_margin_pct"].round(4)
    agg["total_revenue"]  = agg["total_revenue"].round(2)
    agg = agg.sort_values("total_revenue", ascending=False).reset_index(drop=True)

    return agg
