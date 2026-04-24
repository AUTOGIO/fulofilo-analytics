"""
FulôFiló — Product Classification Engine
=========================================
Assigns a strategic quadrant label to each product based on fixed business
thresholds for volume (qty_sold) and margin (margin_pct).

Classification rules:
  - Star       → qty_sold >= vol_threshold  AND margin_pct >= margin_threshold
  - Cash Cow   → qty_sold >= vol_threshold  AND margin_pct <  margin_threshold
  - Hidden Gem → qty_sold <  vol_threshold  AND margin_pct >= margin_threshold
  - Dog        → qty_sold <  vol_threshold  AND margin_pct <  margin_threshold

Fixed thresholds (default, use_fixed_thresholds=True):
  FIXED_MARGIN_THRESHOLD = 35.0  — 35% margin floor (0–100 scale)
  FIXED_QTY_THRESHOLD    = 50    — 50 units sold floor
  These ensure consistent quadrant positions across category filters and time.

Dynamic thresholds (use_fixed_thresholds=False):
  Thresholds computed from dataset median — useful for exploratory analysis.

Required columns: qty_sold (numeric), margin_pct (numeric, 0–100 scale)
Optional columns: any additional columns pass through unchanged.

Public API
----------
classify_dataframe(df, use_fixed_thresholds=True) → pd.DataFrame
    Enriches the input DataFrame with a 'classification' column.
    Returns a copy; does not mutate input.

classify_product(qty_sold, margin_pct, vol_threshold, margin_threshold) → str
    Classifies a single product given explicit thresholds.
    Used internally and by tests.

compute_thresholds(df, use_fixed=True) → (float, float)
    Returns (vol_threshold, margin_threshold).
    If use_fixed=True, returns business constants; else returns medians.
"""

from __future__ import annotations

import logging
from typing import Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# ── Classification labels ──────────────────────────────────────────────────────
STAR        = "Star"
CASH_COW    = "Cash Cow"
HIDDEN_GEM  = "Hidden Gem"
DOG         = "Dog"
UNKNOWN     = "Unknown"

REQUIRED_COLUMNS = {"qty_sold", "margin_pct"}

# ── Fixed business thresholds (0–100 scale for margin_pct) ────────────────────
# These are stable across filters and periods — change only on business review.
FIXED_MARGIN_THRESHOLD: float = 35.0   # 35% gross margin floor
FIXED_QTY_THRESHOLD: float    = 50.0   # 50 units sold floor


# ── Core helpers ───────────────────────────────────────────────────────────────

def compute_thresholds(df: pd.DataFrame, use_fixed: bool = True) -> Tuple[float, float]:
    """
    Return (vol_threshold, margin_threshold) for quadrant classification.

    Parameters
    ----------
    df        : product DataFrame with qty_sold and margin_pct columns.
    use_fixed : if True (default), returns FIXED_QTY_THRESHOLD /
                FIXED_MARGIN_THRESHOLD regardless of data distribution.
                if False, computes medians from df (legacy dynamic mode).

    Returns
    -------
    (vol_threshold, margin_threshold) as floats.
    Falls back to 0.0 per axis if column is empty or all-null (dynamic mode).
    """
    if use_fixed:
        return FIXED_QTY_THRESHOLD, FIXED_MARGIN_THRESHOLD

    vol_threshold    = float(df["qty_sold"].median())    if not df["qty_sold"].isna().all()    else 0.0
    margin_threshold = float(df["margin_pct"].median())  if not df["margin_pct"].isna().all()  else 0.0
    return vol_threshold, margin_threshold


def classify_product(
    qty_sold: float,
    margin_pct: float,
    vol_threshold: float,
    margin_threshold: float,
) -> str:
    """
    Classify a single product given explicit thresholds.

    Parameters
    ----------
    qty_sold         : quantity sold (numeric)
    margin_pct       : margin percentage in 0–1 decimal scale
    vol_threshold    : volume threshold (typically median qty_sold)
    margin_threshold : margin threshold (typically median margin_pct)

    Returns
    -------
    One of: "Star", "Cash Cow", "Hidden Gem", "Dog", "Unknown"
    """
    try:
        qty    = float(qty_sold)
        margin = float(margin_pct)
    except (TypeError, ValueError):
        return UNKNOWN

    high_vol    = qty    >= vol_threshold
    high_margin = margin >= margin_threshold

    if high_vol and high_margin:
        return STAR
    if high_vol and not high_margin:
        return CASH_COW
    if not high_vol and high_margin:
        return HIDDEN_GEM
    return DOG


# ── Public API ─────────────────────────────────────────────────────────────────

def classify_dataframe(df: pd.DataFrame, use_fixed_thresholds: bool = True) -> pd.DataFrame:
    """
    Enrich a product DataFrame with a 'classification' column.

    Parameters
    ----------
    df                    : pd.DataFrame
        Must contain 'qty_sold' and 'margin_pct' columns.
        All other columns pass through unchanged.
    use_fixed_thresholds  : bool, default True
        If True, uses FIXED_QTY_THRESHOLD / FIXED_MARGIN_THRESHOLD for
        deterministic, filter-stable quadrant assignment.
        If False, uses dataset medians (legacy dynamic mode).

    Returns
    -------
    A copy of df with 'classification' column added (or overwritten).
    Rows with null qty_sold or null margin_pct receive 'Unknown'.

    Behavior on edge cases
    ----------------------
    - Empty DataFrame   → returns empty DataFrame with 'classification' column
    - Missing columns   → raises ValueError with clear message
    - All-null columns  → all rows receive 'Unknown'
    - Single row        → classified against fixed thresholds (if use_fixed=True)
    """
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"classify_dataframe: missing required columns: {missing}. "
            f"Available columns: {list(df.columns)}"
        )

    if df.empty:
        result = df.copy()
        result["classification"] = pd.Series(dtype="string")
        logger.warning("classify_dataframe: received empty DataFrame, returning empty result.")
        return result

    result = df.copy()

    # Drop rows that are null in both axes to compute clean thresholds,
    # but still classify ALL original rows (nulls → Unknown).
    valid_mask = result["qty_sold"].notna() & result["margin_pct"].notna()
    valid_df   = result[valid_mask]

    if valid_df.empty:
        logger.warning("classify_dataframe: all qty_sold/margin_pct values are null → all Unknown.")
        result["classification"] = UNKNOWN
        return result

    vol_threshold, margin_threshold = compute_thresholds(valid_df, use_fixed=use_fixed_thresholds)
    logger.info(
        "classify_dataframe: thresholds [%s] — vol=%.2f, margin=%.2f",
        "fixed" if use_fixed_thresholds else "dynamic",
        vol_threshold,
        margin_threshold,
    )

    result["classification"] = result.apply(
        lambda row: classify_product(
            row["qty_sold"],
            row["margin_pct"],
            vol_threshold,
            margin_threshold,
        )
        if pd.notna(row["qty_sold"]) and pd.notna(row["margin_pct"])
        else UNKNOWN,
        axis=1,
    )

    # Validate: every row must have a classification
    null_count = result["classification"].isna().sum()
    if null_count:
        logger.error("classify_dataframe: %d rows have null classification (unexpected).", null_count)
        result["classification"] = result["classification"].fillna(UNKNOWN)

    counts = result["classification"].value_counts().to_dict()
    logger.info("classify_dataframe: distribution → %s", counts)

    return result
