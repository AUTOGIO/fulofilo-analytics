"""
FulôFiló — ABC Decision Engine
================================
Assigns action tags and generates specific recommendations for each product
based on its ABC Pareto class (A/B/C), quantity sold, margin, and revenue.

Distinct from core/recommendations.py, which uses the volume×margin quadrant
system (Star/Cash Cow/Hidden Gem/Dog). This module operates exclusively on
the abc_class field produced by the Pareto classification.

Thresholds
----------
All thresholds are configurable via the `thresholds` parameter.
Defaults are computed from the dataset (25th/50th percentiles) so the engine
adapts automatically to different product catalogs.

Default threshold keys
  qty_low      : qty_sold below this → Class A product needs urgent restock
  margin_high  : margin_pct above this → Class B can test a price increase
  revenue_low  : revenue below this → Class C is a discontinuation candidate

Public API
----------
assign_action_tag(classe: str) → str
    "A" → "🔥 SCALE" | "B" → "⚙️ OPTIMIZE" | "C" → "🧹 REDUCE"

compute_default_thresholds(df: pd.DataFrame) → dict
    Derive dataset-specific thresholds (25th/50th percentile).

generate_recommendation(product: dict, thresholds: dict) → dict
    Return {"recommendation": str, "priority": str} for one product.

enrich_with_decisions(df: pd.DataFrame, thresholds: dict | None) → pd.DataFrame
    Add action_tag, recommendation, priority, last_updated columns.
    Backward compatible — never overwrites existing columns.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ── Action tags ───────────────────────────────────────────────────────────────

ACTION_TAGS: dict[str, str] = {
    "A": "🔥 SCALE",
    "B": "⚙️ OPTIMIZE",
    "C": "🧹 REDUCE",
}

# ── Fallback thresholds (used when dataset is empty / columns are missing) ────
# margin_pct is stored in percentage units (e.g. 48.0 = 48%) across this repo.

_FALLBACK_THRESHOLDS: dict[str, float] = {
    "qty_low":     10.0,    # units sold — below this = low-stock alert for Class A
    "margin_high": 45.0,    # percent — above this = good margin for Class B
    "revenue_low": 1000.0,  # R$ — below this = weak Class C candidate for exit
}


# ── Public API ─────────────────────────────────────────────────────────────────

def assign_action_tag(classe: str) -> str:
    """
    Return the visual action tag for an ABC class.

    Parameters
    ----------
    classe : str — "A", "B", or "C" (case-insensitive)

    Returns
    -------
    str — one of "🔥 SCALE", "⚙️ OPTIMIZE", "🧹 REDUCE", or "❓ REVIEW"
    """
    tag = ACTION_TAGS.get(str(classe).strip().upper())
    if tag is None:
        logger.warning("assign_action_tag: unrecognized class '%s'. Using fallback.", classe)
        return "❓ REVIEW"
    return tag


def compute_default_thresholds(df: pd.DataFrame) -> dict[str, float]:
    """
    Derive thresholds from the dataset using percentile statistics.

    Parameters
    ----------
    df : pd.DataFrame — product catalog with qty_sold, margin_pct, revenue

    Returns
    -------
    dict — keys: qty_low, margin_high, revenue_low
    Falls back to _FALLBACK_THRESHOLDS for any missing or empty column.
    """
    thresholds = dict(_FALLBACK_THRESHOLDS)

    if df.empty:
        return thresholds

    if "qty_sold" in df.columns:
        valid = df["qty_sold"].dropna()
        if not valid.empty:
            thresholds["qty_low"] = float(valid.quantile(0.25))

    if "margin_pct" in df.columns:
        valid = df["margin_pct"].dropna()
        if not valid.empty:
            thresholds["margin_high"] = float(valid.median())

    if "revenue" in df.columns:
        valid = df["revenue"].dropna()
        if not valid.empty:
            thresholds["revenue_low"] = float(valid.quantile(0.25))

    return thresholds


def generate_recommendation(
    product: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, str]:
    """
    Generate a specific recommendation for a single product.

    Parameters
    ----------
    product    : dict — must contain abc_class, qty_sold, margin_pct, revenue
    thresholds : dict — from compute_default_thresholds() or custom overrides

    Returns
    -------
    dict with:
      recommendation : str — concrete action instruction
      priority       : str — "HIGH" | "MEDIUM" | "LOW"

    Rules
    -----
    Class A:
      qty_sold < qty_low  → "RESTOCK URGENTLY"            (HIGH)
      otherwise           → "MAINTAIN STOCK + TEST PRICE INCREASE" (HIGH)

    Class B:
      margin_pct > margin_high → "TEST PRICE INCREASE"          (MEDIUM)
      otherwise                → "IMPROVE VISIBILITY / PROMOTION" (MEDIUM)

    Class C:
      revenue < revenue_low → "CONSIDER DISCONTINUATION"  (LOW)
      otherwise             → "BUNDLE WITH A PRODUCTS"    (LOW)
    """
    classe     = str(product.get("abc_class", "")).strip().upper()
    qty_sold   = float(product.get("qty_sold")   or 0)
    margin_pct = float(product.get("margin_pct") or 0)
    revenue    = float(product.get("revenue")    or 0)

    qty_low      = float(thresholds.get("qty_low",      _FALLBACK_THRESHOLDS["qty_low"]))
    margin_high  = float(thresholds.get("margin_high",  _FALLBACK_THRESHOLDS["margin_high"]))
    revenue_low  = float(thresholds.get("revenue_low",  _FALLBACK_THRESHOLDS["revenue_low"]))

    if classe == "A":
        if qty_sold < qty_low:
            return {"recommendation": "RESTOCK URGENTLY", "priority": "HIGH"}
        return {"recommendation": "MAINTAIN STOCK + TEST PRICE INCREASE", "priority": "HIGH"}

    if classe == "B":
        if margin_pct > margin_high:
            return {"recommendation": "TEST PRICE INCREASE", "priority": "MEDIUM"}
        return {"recommendation": "IMPROVE VISIBILITY / PROMOTION", "priority": "MEDIUM"}

    if classe == "C":
        if revenue < revenue_low:
            return {"recommendation": "CONSIDER DISCONTINUATION", "priority": "LOW"}
        return {"recommendation": "BUNDLE WITH A PRODUCTS", "priority": "LOW"}

    logger.warning("generate_recommendation: unknown abc_class '%s'.", classe)
    return {"recommendation": "REVIEW MANUALLY", "priority": "LOW"}


def enrich_with_decisions(
    df: pd.DataFrame,
    thresholds: dict[str, float] | None = None,
) -> pd.DataFrame:
    """
    Add decision intelligence columns to a product DataFrame.

    Parameters
    ----------
    df         : pd.DataFrame — must have abc_class, qty_sold, margin_pct, revenue
    thresholds : dict | None — uses compute_default_thresholds(df) if None

    Returns
    -------
    A copy of df with four new columns appended:
      action_tag     : str — "🔥 SCALE" | "⚙️ OPTIMIZE" | "🧹 REDUCE"
      recommendation : str — specific actionable instruction
      priority       : str — "HIGH" | "MEDIUM" | "LOW"
      last_updated   : str — ISO 8601 timestamp (UTC)

    Backward compatible — does not overwrite columns that already exist.
    Does not mutate the input DataFrame.
    """
    if df.empty:
        result = df.copy()
        for col in ("action_tag", "recommendation", "priority", "last_updated"):
            if col not in result.columns:
                result[col] = pd.Series(dtype="string")
        return result

    result = df.copy()
    thr = thresholds if thresholds is not None else compute_default_thresholds(df)
    now_iso = datetime.now(timezone.utc).isoformat()

    def _decide(row: pd.Series) -> pd.Series:
        rec = generate_recommendation(row.to_dict(), thr)
        return pd.Series({
            "action_tag":     assign_action_tag(row.get("abc_class", "")),
            "recommendation": rec["recommendation"],
            "priority":       rec["priority"],
            "last_updated":   now_iso,
        })

    decisions = result.apply(_decide, axis=1)

    for col in ("action_tag", "recommendation", "priority", "last_updated"):
        result[col] = decisions[col]

    logger.info(
        "enrich_with_decisions: enriched %d products | thresholds=%s",
        len(result), thr,
    )
    return result
