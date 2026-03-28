"""
FulôFiló — Basic Alerts Engine
================================
Generates a list of actionable alerts by joining product classification data
with inventory stock levels.

Alert rules
-----------
  ACTIVE (both products + inventory data available):
    1. Star with low stock     → current_stock <= min_stock
    2. Dog with high stock     → current_stock > reorder_qty (overstock on a poor performer)

  DEGRADED (requires historical volume trend — not available in current schema):
    3. Hidden Gem with rising volume → SKIPPED (no time-series volume data present)

All alert rules that cannot run due to missing data are documented in the
returned `skipped_rules` list rather than silently failing or inventing data.

Required data
-------------
  products_df  : pd.DataFrame — must have: slug, full_name, category,
                 qty_sold, revenue, margin_pct, classification
  inventory_df : pd.DataFrame — must have: slug, current_stock, min_stock, reorder_qty

Public API
----------
generate_alerts(products_df, inventory_df=None) → dict
    Returns:
        {
          "alerts":        [list of alert dicts],
          "skipped_rules": [list of rule names that were skipped + reason],
          "summary":       {total, by_severity},
        }

Alert dict structure
--------------------
    {
      "rule":        str  — rule identifier
      "severity":    str  — "high" | "medium" | "low"
      "slug":        str  — product code
      "product":     str  — display name
      "category":    str  — category
      "classification": str
      "message":     str  — human-readable alert text
      "current_stock": int | None
      "min_stock":   int | None
    }
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from core.classification import STAR, CASH_COW, HIDDEN_GEM, DOG

logger = logging.getLogger(__name__)

# ── Alert rule identifiers ─────────────────────────────────────────────────────
RULE_STAR_LOW_STOCK   = "star_low_stock"
RULE_DOG_HIGH_STOCK   = "dog_high_stock"
RULE_GEM_RISING_VOL   = "hidden_gem_rising_volume"

# Fields required for each rule
_RULE_REQUIREMENTS = {
    RULE_STAR_LOW_STOCK: {"products": {"slug", "full_name", "classification"},
                          "inventory": {"slug", "current_stock", "min_stock"}},
    RULE_DOG_HIGH_STOCK: {"products": {"slug", "full_name", "classification"},
                          "inventory": {"slug", "current_stock", "reorder_qty"}},
    RULE_GEM_RISING_VOL: {"products": {"slug", "full_name", "classification"},
                          "inventory": None,  # needs historical data — not available
                          "note": "Requires time-series volume history not present in current schema."},
}


# ── Internal helpers ───────────────────────────────────────────────────────────

def _check_rule_feasibility(
    rule: str,
    products_cols: set[str],
    inventory_cols: set[str] | None,
) -> tuple[bool, str]:
    """
    Check whether a rule can run given the available columns.
    Returns (can_run: bool, reason: str).
    """
    req = _RULE_REQUIREMENTS.get(rule, {})

    # Rules that explicitly require missing data
    if req.get("note"):
        return False, req["note"]

    prod_required = req.get("products", set())
    inv_required  = req.get("inventory", set())

    missing_prod = prod_required - products_cols
    if missing_prod:
        return False, f"Products missing columns: {missing_prod}"

    if inv_required:
        if inventory_cols is None:
            return False, "No inventory data provided"
        missing_inv = inv_required - inventory_cols
        if missing_inv:
            return False, f"Inventory missing columns: {missing_inv}"

    return True, "ok"


def _build_alert(
    rule: str,
    severity: str,
    row: pd.Series,
    message: str,
    inv_row: pd.Series | None = None,
) -> dict[str, Any]:
    """Construct a standardised alert dict."""
    return {
        "rule":           rule,
        "severity":       severity,
        "slug":           row.get("slug"),
        "product":        row.get("full_name") or row.get("product", "Unknown"),
        "category":       row.get("category"),
        "classification": row.get("classification"),
        "message":        message,
        "current_stock":  int(inv_row["current_stock"]) if inv_row is not None and pd.notna(inv_row.get("current_stock")) else None,
        "min_stock":      int(inv_row["min_stock"])     if inv_row is not None and pd.notna(inv_row.get("min_stock"))     else None,
        "reorder_qty":    int(inv_row["reorder_qty"])   if inv_row is not None and pd.notna(inv_row.get("reorder_qty"))   else None,
        "qty_sold":       row.get("qty_sold"),
        "revenue":        row.get("revenue"),
    }


# ── Alert rule implementations ────────────────────────────────────────────────

def _rule_star_low_stock(
    products_df: pd.DataFrame,
    merged_df: pd.DataFrame,
) -> list[dict]:
    """Star products where current_stock <= min_stock."""
    stars   = merged_df[merged_df["classification"] == STAR].copy()
    low     = stars[stars["current_stock"] <= stars["min_stock"]]
    alerts  = []
    for _, row in low.iterrows():
        alerts.append(_build_alert(
            rule       = RULE_STAR_LOW_STOCK,
            severity   = "high",
            row        = row,
            message    = (
                f"⭐ Star product '{row.get('full_name')}' has LOW STOCK "
                f"(current: {int(row['current_stock'])} ≤ min: {int(row['min_stock'])}). "
                f"Replenish immediately."
            ),
            inv_row    = row,
        ))
    return alerts


def _rule_dog_high_stock(
    products_df: pd.DataFrame,
    merged_df: pd.DataFrame,
) -> list[dict]:
    """Dog products where current_stock > reorder_qty (overstock on poor performers)."""
    dogs    = merged_df[merged_df["classification"] == DOG].copy()
    high    = dogs[dogs["current_stock"] > dogs["reorder_qty"]]
    alerts  = []
    for _, row in high.iterrows():
        alerts.append(_build_alert(
            rule       = RULE_DOG_HIGH_STOCK,
            severity   = "medium",
            row        = row,
            message    = (
                f"🐕 Dog product '{row.get('full_name')}' has HIGH STOCK "
                f"(current: {int(row['current_stock'])} > reorder: {int(row['reorder_qty'])}). "
                f"Consider discounting or discontinuing."
            ),
            inv_row    = row,
        ))
    return alerts


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_alerts(
    products_df: pd.DataFrame,
    inventory_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """
    Generate operational alerts by applying all available rules.

    Parameters
    ----------
    products_df  : pd.DataFrame enriched with 'classification' column.
                   Required columns: slug, full_name, category, classification.
    inventory_df : pd.DataFrame | None.
                   Required columns: slug, current_stock, min_stock, reorder_qty.
                   If None, only rules that don't need inventory will run.

    Returns
    -------
    dict with keys:
        alerts        : list[dict] — all generated alerts
        skipped_rules : list[dict] — rules that could not run + reason
        summary       : dict with total count and breakdown by severity
    """
    if products_df.empty:
        logger.warning("generate_alerts: empty products_df — no alerts generated.")
        return {
            "alerts": [],
            "skipped_rules": [{"rule": r, "reason": "No product data available"} for r in _RULE_REQUIREMENTS],
            "summary": {"total": 0, "high": 0, "medium": 0, "low": 0},
        }

    products_cols  = set(products_df.columns)
    inventory_cols = set(inventory_df.columns) if inventory_df is not None and not inventory_df.empty else None

    all_alerts:    list[dict] = []
    skipped_rules: list[dict] = []

    # ── Merge products + inventory (left join on slug) ─────────────────────────
    merged_df = None
    if inventory_df is not None and not inventory_df.empty and "slug" in products_cols and "slug" in inventory_cols:
        try:
            merged_df = products_df.merge(inventory_df, on="slug", how="left", suffixes=("", "_inv"))
        except Exception as exc:
            logger.error("generate_alerts: merge failed — %s. Inventory-dependent rules skipped.", exc)
            merged_df = None

    # ── Rule: star_low_stock ──────────────────────────────────────────────────
    can_run, reason = _check_rule_feasibility(RULE_STAR_LOW_STOCK, products_cols, inventory_cols)
    if can_run and merged_df is not None:
        try:
            alerts = _rule_star_low_stock(products_df, merged_df)
            all_alerts.extend(alerts)
            logger.info("Rule '%s': %d alerts.", RULE_STAR_LOW_STOCK, len(alerts))
        except Exception as exc:
            logger.error("Rule '%s' raised: %s", RULE_STAR_LOW_STOCK, exc)
            skipped_rules.append({"rule": RULE_STAR_LOW_STOCK, "reason": f"Runtime error: {exc}"})
    else:
        skipped_rules.append({"rule": RULE_STAR_LOW_STOCK, "reason": reason})
        logger.info("Rule '%s' skipped: %s", RULE_STAR_LOW_STOCK, reason)

    # ── Rule: dog_high_stock ──────────────────────────────────────────────────
    can_run, reason = _check_rule_feasibility(RULE_DOG_HIGH_STOCK, products_cols, inventory_cols)
    if can_run and merged_df is not None:
        try:
            alerts = _rule_dog_high_stock(products_df, merged_df)
            all_alerts.extend(alerts)
            logger.info("Rule '%s': %d alerts.", RULE_DOG_HIGH_STOCK, len(alerts))
        except Exception as exc:
            logger.error("Rule '%s' raised: %s", RULE_DOG_HIGH_STOCK, exc)
            skipped_rules.append({"rule": RULE_DOG_HIGH_STOCK, "reason": f"Runtime error: {exc}"})
    else:
        skipped_rules.append({"rule": RULE_DOG_HIGH_STOCK, "reason": reason})
        logger.info("Rule '%s' skipped: %s", RULE_DOG_HIGH_STOCK, reason)

    # ── Rule: hidden_gem_rising_volume (always degraded — no historical data) ─
    can_run, reason = _check_rule_feasibility(RULE_GEM_RISING_VOL, products_cols, inventory_cols)
    # Will always be False because of the "note" field
    skipped_rules.append({"rule": RULE_GEM_RISING_VOL, "reason": reason})
    logger.info("Rule '%s' skipped: %s", RULE_GEM_RISING_VOL, reason)

    # ── Summary ───────────────────────────────────────────────────────────────
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for a in all_alerts:
        sev = a.get("severity", "low")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    return {
        "alerts":        all_alerts,
        "skipped_rules": skipped_rules,
        "summary": {
            "total": len(all_alerts),
            **severity_counts,
        },
    }
