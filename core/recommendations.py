"""
FulôFiló — Action Recommendation Engine
=========================================
Maps a product classification label to a concrete recommended action.

The mapping is intentionally centralized here so that:
  - dashboard, reporting, and alerts all reference the same source of truth
  - new classifications or actions can be added in one place
  - the mapping can be extended to per-category or per-product overrides later

Public API
----------
get_recommendation(classification) → str
    Returns the recommended action string for a given classification label.

enrich_with_recommendations(df) → pd.DataFrame
    Adds a 'recommended_action' column to a DataFrame that already has
    a 'classification' column. Returns a copy; does not mutate input.
"""

from __future__ import annotations

import logging

import pandas as pd

from core.classification import STAR, CASH_COW, HIDDEN_GEM, DOG, UNKNOWN

logger = logging.getLogger(__name__)

# ── Recommendation mapping ─────────────────────────────────────────────────────
# Centralized. Extend here — do not scatter mappings across modules.

ACTION_MAP: dict[str, str] = {
    STAR:       "Scale stock + ads + test price increase",
    CASH_COW:   "Optimize cost + bundle",
    HIDDEN_GEM: "Increase visibility + test campaigns",
    DOG:        "Fix or discontinue",
    UNKNOWN:    "Insufficient data — review manually",
}

# Human-readable emoji prefix for dashboard display
DISPLAY_MAP: dict[str, str] = {
    STAR:       "🌟 Scale stock + ads + test price increase",
    CASH_COW:   "🐄 Optimize cost + bundle",
    HIDDEN_GEM: "💎 Increase visibility + test campaigns",
    DOG:        "🐕 Fix or discontinue",
    UNKNOWN:    "⚠️ Insufficient data — review manually",
}


# ── Public API ─────────────────────────────────────────────────────────────────

def get_recommendation(classification: str, display: bool = False) -> str:
    """
    Return the recommended action for a given classification label.

    Parameters
    ----------
    classification : str
        One of the classification constants (Star, Cash Cow, etc.)
    display : bool
        If True, returns the emoji-prefixed display string.
        If False (default), returns the plain machine-readable string.

    Returns
    -------
    str — never returns None or raises for valid/unknown classification.
    """
    mapping = DISPLAY_MAP if display else ACTION_MAP
    recommendation = mapping.get(classification)

    if recommendation is None:
        logger.warning(
            "get_recommendation: unrecognized classification '%s'. "
            "Returning fallback. Check classification.py for valid labels.",
            classification,
        )
        recommendation = mapping.get(UNKNOWN, "Review manually")

    return recommendation


def enrich_with_recommendations(df: pd.DataFrame, display: bool = True) -> pd.DataFrame:
    """
    Add a 'recommended_action' column to a DataFrame with a 'classification' column.

    Parameters
    ----------
    df      : pd.DataFrame with a 'classification' column (str)
    display : bool — if True, uses emoji-prefixed display strings (default True)

    Returns
    -------
    A copy of df with 'recommended_action' added (or overwritten).
    Rows with null classification receive the UNKNOWN fallback action.

    Raises
    ------
    ValueError if 'classification' column is missing.
    """
    if "classification" not in df.columns:
        raise ValueError(
            "enrich_with_recommendations: 'classification' column is required. "
            "Call classify_dataframe() first."
        )

    if df.empty:
        result = df.copy()
        result["recommended_action"] = pd.Series(dtype="string")
        return result

    result = df.copy()
    result["recommended_action"] = result["classification"].apply(
        lambda c: get_recommendation(c if pd.notna(c) else UNKNOWN, display=display)
    )

    null_actions = result["recommended_action"].isna().sum()
    if null_actions:
        logger.error(
            "enrich_with_recommendations: %d rows have null recommended_action (unexpected).",
            null_actions,
        )
        result["recommended_action"] = result["recommended_action"].fillna(
            get_recommendation(UNKNOWN, display=display)
        )

    return result
