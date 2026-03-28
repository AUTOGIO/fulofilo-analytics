"""
FulôFiló — Weekly Decision Report Generator
=============================================
Produces a structured JSON report from the enriched product dataset.

Report sections
---------------
  metadata        : generation timestamp, row counts, thresholds used
  stars           : top Star products (priority stock)
  hidden_gems     : top Hidden Gem products (growth opportunities)
  dogs            : Dog products (candidates for review/discontinuation)
  cash_cows       : Cash Cow products (operational base)
  revenue_concentration : top 20% of products by revenue (Pareto analysis)
    Interpretation: the N products whose cumulative revenue >= 80% of total.
    This identifies the critical minority that drives the majority of income.

Output
------
  - Mandatory: JSON file at data/outputs/weekly_report.json
  - Optional:  Markdown summary at data/outputs/weekly_report.md
  - Returns:   dict (the same structure written to JSON)

Public API
----------
generate_weekly_report(data, save_path=None, save_md=True) → dict
    data       : pd.DataFrame enriched with 'classification' and 'recommended_action'
    save_path  : Path to output JSON (default: data/outputs/weekly_report.json)
    save_md    : bool — also write a Markdown summary (default True)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from core.classification import STAR, CASH_COW, HIDDEN_GEM, DOG, compute_thresholds

logger = logging.getLogger(__name__)

# ── Defaults ───────────────────────────────────────────────────────────────────
_ROOT        = Path(__file__).resolve().parent.parent
_DEFAULT_OUT = _ROOT / "data" / "outputs" / "weekly_report.json"
_DEFAULT_MD  = _ROOT / "data" / "outputs" / "weekly_report.md"

_PRODUCT_COLS = ["slug", "full_name", "category", "qty_sold", "revenue", "margin_pct",
                 "classification", "recommended_action"]


# ── Internal helpers ───────────────────────────────────────────────────────────

def _safe_records(df: pd.DataFrame, cols: list[str]) -> list[dict]:
    """Extract records from df for a subset of columns that actually exist.
    Fills NaN → None so JSON serialisation never fails."""
    available = [c for c in cols if c in df.columns]
    subset = df[available].copy()
    subset = subset.where(subset.notna(), other=None)
    return subset.to_dict(orient="records")


def _revenue_concentration(df: pd.DataFrame, top_pct: float = 0.20) -> dict[str, Any]:
    """
    Pareto analysis: identify the smallest group of products whose cumulative
    revenue >= (1 - top_pct) of total revenue, i.e. the top-20% revenue drivers.

    Interpretation used here:
      Sort products descending by revenue.
      Walk the list until cumulative revenue >= 80% of total.
      The products included are the 'top 20% revenue concentration'.

    Returns a dict with:
      - threshold_pct   : 0.80 (revenue target)
      - n_products      : count of products in group
      - pct_of_catalog  : fraction of SKUs this represents
      - total_revenue   : total revenue across ALL products
      - group_revenue   : cumulative revenue of the concentration group
      - products        : list of product records in the group
    """
    if df.empty or "revenue" not in df.columns:
        return {"error": "No revenue data available"}

    total_revenue = float(df["revenue"].sum())
    if total_revenue == 0:
        return {"error": "Total revenue is zero"}

    revenue_target = total_revenue * (1.0 - top_pct)

    sorted_df = df.sort_values("revenue", ascending=False).reset_index(drop=True)
    sorted_df["cumulative_revenue"] = sorted_df["revenue"].cumsum()

    cutoff_mask = sorted_df["cumulative_revenue"] <= revenue_target
    # Include one more row to cross the threshold
    cutoff_idx  = cutoff_mask.sum()
    group_df    = sorted_df.iloc[: cutoff_idx + 1]

    return {
        "threshold_pct":  1.0 - top_pct,
        "n_products":     int(len(group_df)),
        "pct_of_catalog": round(len(group_df) / len(df), 4) if len(df) > 0 else 0.0,
        "total_revenue":  round(total_revenue, 2),
        "group_revenue":  round(float(group_df["revenue"].sum()), 2),
        "products":       _safe_records(group_df.head(10), _PRODUCT_COLS),
    }


def _section(df: pd.DataFrame, label: str, sort_col: str, top_n: int = 10) -> list[dict]:
    """Return top_n records for a given classification label, sorted descending."""
    subset = df[df["classification"] == label].sort_values(sort_col, ascending=False)
    return _safe_records(subset.head(top_n), _PRODUCT_COLS)


def _markdown_summary(report: dict) -> str:
    """Generate a compact Markdown summary from the report dict."""
    ts   = report.get("metadata", {}).get("generated_at", "")
    lines = [
        f"# FulôFiló — Weekly Decision Report",
        f"_Generated: {ts}_",
        "",
        "## 🌟 Stars (Top 5)",
    ]
    for p in report.get("stars", [])[:5]:
        lines.append(
            f"- **{p.get('full_name', '?')}** | "
            f"Rev: R$ {p.get('revenue', 0):,.2f} | "
            f"Margin: {p.get('margin_pct', 0)*100:.1f}% | "
            f"{p.get('recommended_action', '')}"
        )
    lines += ["", "## 💎 Hidden Gems (Top 5)"]
    for p in report.get("hidden_gems", [])[:5]:
        lines.append(
            f"- **{p.get('full_name', '?')}** | "
            f"Rev: R$ {p.get('revenue', 0):,.2f} | "
            f"Margin: {p.get('margin_pct', 0)*100:.1f}%"
        )
    lines += ["", "## 🐕 Dogs (candidates for review)"]
    for p in report.get("dogs", [])[:5]:
        lines.append(
            f"- **{p.get('full_name', '?')}** | "
            f"Rev: R$ {p.get('revenue', 0):,.2f} | "
            f"Qty: {p.get('qty_sold', 0)}"
        )
    conc = report.get("revenue_concentration", {})
    lines += [
        "",
        "## 📊 Revenue Concentration (Pareto 80%)",
        f"- **{conc.get('n_products', '?')} products** drive "
        f"{conc.get('threshold_pct', 0.8)*100:.0f}% of revenue "
        f"({conc.get('pct_of_catalog', 0)*100:.1f}% of catalog)",
    ]
    return "\n".join(lines)


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_weekly_report(
    data: pd.DataFrame,
    save_path: Path | None = None,
    save_md:   bool = True,
) -> dict:
    """
    Generate the weekly decision report from an enriched product DataFrame.

    Parameters
    ----------
    data      : pd.DataFrame — must have columns from classify_dataframe()
                and enrich_with_recommendations().
                Required: qty_sold, margin_pct, revenue, classification, recommended_action
    save_path : Path | None — JSON output path. Defaults to data/outputs/weekly_report.json
    save_md   : bool — also write a Markdown file (default True)

    Returns
    -------
    dict — the full report structure (same as written to JSON).

    Behavior on edge cases
    ----------------------
    - Empty DataFrame → returns a minimal report with empty sections and no file write
    - Missing columns → gracefully skips affected sections, logs warnings
    - NaN values      → replaced with None before JSON serialisation
    """
    out_path = Path(save_path) if save_path else _DEFAULT_OUT
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if data.empty:
        logger.warning("generate_weekly_report: received empty DataFrame. Returning empty report.")
        return {
            "metadata": {"generated_at": datetime.now(timezone.utc).isoformat(), "status": "empty"},
            "stars": [], "hidden_gems": [], "dogs": [], "cash_cows": [],
            "revenue_concentration": {},
        }

    # ── Validate required columns ──────────────────────────────────────────────
    required = {"qty_sold", "margin_pct", "revenue", "classification", "recommended_action"}
    missing  = required - set(data.columns)
    if missing:
        logger.warning("generate_weekly_report: missing columns %s — affected sections will be empty.", missing)

    df = data.copy()

    # ── Compute thresholds for metadata ───────────────────────────────────────
    vol_thr, margin_thr = (0.0, 0.0)
    if {"qty_sold", "margin_pct"}.issubset(df.columns):
        valid = df[df["qty_sold"].notna() & df["margin_pct"].notna()]
        if not valid.empty:
            vol_thr, margin_thr = compute_thresholds(valid)

    # ── Distribution ──────────────────────────────────────────────────────────
    if "classification" in df.columns:
        distribution = df["classification"].value_counts().to_dict()
    else:
        distribution = {}

    # ── Build report ──────────────────────────────────────────────────────────
    report: dict[str, Any] = {
        "metadata": {
            "generated_at":     datetime.now(timezone.utc).isoformat(),
            "total_products":   int(len(df)),
            "classified":       int(df["classification"].notna().sum()) if "classification" in df.columns else 0,
            "distribution":     distribution,
            "thresholds": {
                "vol_threshold":    round(vol_thr, 2),
                "margin_threshold": round(margin_thr, 4),
                "margin_threshold_pct": f"{margin_thr*100:.1f}%",
            },
            "status": "ok",
        },
        "stars":        _section(df, STAR,       sort_col="revenue")  if "classification" in df.columns else [],
        "cash_cows":    _section(df, CASH_COW,   sort_col="revenue")  if "classification" in df.columns else [],
        "hidden_gems":  _section(df, HIDDEN_GEM, sort_col="margin_pct") if "classification" in df.columns else [],
        "dogs":         _section(df, DOG,        sort_col="revenue",  top_n=15) if "classification" in df.columns else [],
        "revenue_concentration": _revenue_concentration(df) if "revenue" in df.columns else {},
    }

    # ── Serialise + save JSON ──────────────────────────────────────────────────
    try:
        json_str = json.dumps(report, ensure_ascii=False, indent=2, default=str)
        out_path.write_text(json_str, encoding="utf-8")
        logger.info("generate_weekly_report: JSON saved to %s", out_path)
    except Exception as exc:
        logger.error("generate_weekly_report: failed to save JSON — %s", exc)

    # ── Optional Markdown ──────────────────────────────────────────────────────
    if save_md:
        try:
            md_path  = _DEFAULT_MD
            md_text  = _markdown_summary(report)
            md_path.write_text(md_text, encoding="utf-8")
            logger.info("generate_weekly_report: Markdown saved to %s", md_path)
        except Exception as exc:
            logger.warning("generate_weekly_report: Markdown save failed (non-critical) — %s", exc)

    return report
