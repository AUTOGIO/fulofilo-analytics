"""
FulôFiló — ABC Weekly Decision Report
=======================================
Generates a structured JSON/Markdown report from the ABC-enriched product dataset.

This is distinct from core/reporting.py (quadrant-based: Star/Cash Cow/Hidden Gem/Dog).
This module operates on abc_class + decision engine fields (action_tag, recommendation,
priority) produced by core/decision_engine.enrich_with_decisions().

Report sections
---------------
  metadata        : timestamp, totals, thresholds, class distribution
  scale           : top 5 Class A products (SCALE actions), sorted by revenue
  optimize        : top 5 Class B products (OPTIMIZE actions), sorted by revenue
  reduce          : top 5 Class C products (REDUCE actions), sorted by revenue asc
  urgent_restock  : Class A products flagged "RESTOCK URGENTLY" (priority = HIGH)
  exit_candidates : Class C products flagged "CONSIDER DISCONTINUATION"

Output
------
  data/outputs/abc_weekly_report.json   (always written)
  data/outputs/abc_weekly_report.md     (written when save_md=True)

Public API
----------
generate_abc_report(df, save_path=None, save_md=True) → dict
    df must be enriched with core/decision_engine.enrich_with_decisions().
    Required columns: abc_class, revenue, qty_sold, margin_pct,
                      action_tag, recommendation, priority
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from core.decision_engine import compute_default_thresholds, enrich_with_decisions

logger = logging.getLogger(__name__)

# ── Defaults ───────────────────────────────────────────────────────────────────
_ROOT        = Path(__file__).resolve().parent.parent
_DEFAULT_OUT = _ROOT / "data" / "outputs" / "abc_weekly_report.json"
_DEFAULT_MD  = _ROOT / "data" / "outputs" / "abc_weekly_report.md"

_PRODUCT_COLS = [
    "sku", "full_name", "category",
    "qty_sold", "revenue", "margin_pct", "profit",
    "abc_class", "action_tag", "recommendation", "priority",
]


# ── Internal helpers ───────────────────────────────────────────────────────────

def _safe_records(df: pd.DataFrame, cols: list[str], top_n: int = 5) -> list[dict]:
    """Extract top_n records for available columns; NaN → None for JSON safety."""
    available = [c for c in cols if c in df.columns]
    subset = df[available].head(top_n).copy()
    subset = subset.where(subset.notna(), other=None)
    return subset.to_dict(orient="records")


def _class_section(
    df: pd.DataFrame,
    abc_class: str,
    sort_col: str = "revenue",
    ascending: bool = False,
    top_n: int = 5,
) -> list[dict]:
    """Return top_n records for a given abc_class, sorted by sort_col."""
    subset = df[df["abc_class"] == abc_class].sort_values(sort_col, ascending=ascending)
    return _safe_records(subset, _PRODUCT_COLS, top_n=top_n)


def _recommendation_section(
    df: pd.DataFrame,
    recommendation: str,
    top_n: int = 5,
) -> list[dict]:
    """Return records matching a specific recommendation string."""
    if "recommendation" not in df.columns:
        return []
    subset = df[df["recommendation"] == recommendation].sort_values("revenue", ascending=False)
    return _safe_records(subset, _PRODUCT_COLS, top_n=top_n)


def _class_distribution(df: pd.DataFrame) -> dict[str, int]:
    """Return count per ABC class."""
    if "abc_class" not in df.columns:
        return {}
    return df["abc_class"].value_counts().to_dict()


def _markdown_summary(report: dict) -> str:
    """Generate a compact Markdown decision summary from the report dict."""
    meta = report.get("metadata", {})
    ts   = meta.get("generated_at", "")
    dist = meta.get("distribution", {})
    thr  = meta.get("thresholds", {})

    lines = [
        "# FulôFiló — ABC Weekly Decision Report",
        f"_Generated: {ts}_",
        "",
        "## Distribution",
        f"- 🔥 Class A (SCALE):    {dist.get('A', 0)} products",
        f"- ⚙️  Class B (OPTIMIZE): {dist.get('B', 0)} products",
        f"- 🧹 Class C (REDUCE):   {dist.get('C', 0)} products",
        "",
        f"_Thresholds — qty_low: {thr.get('qty_low', '?'):.0f} units | "
        f"margin_high: {thr.get('margin_high', '?'):.1f}% | "
        f"revenue_low: R$ {thr.get('revenue_low', '?'):.0f}_",
        "",
        "---",
        "",
        "## 🔥 Top 5 — SCALE (Class A)",
    ]
    for p in report.get("scale", []):
        lines.append(
            f"- **{p.get('full_name', '?')}** | "
            f"Rev: R$ {p.get('revenue') or 0:,.2f} | "
            f"Qtd: {p.get('qty_sold') or 0:.0f} | "
            f"_{p.get('recommendation', '')}_"
        )

    lines += ["", "## ⚙️  Top 5 — OPTIMIZE (Class B)"]
    for p in report.get("optimize", []):
        lines.append(
            f"- **{p.get('full_name', '?')}** | "
            f"Rev: R$ {p.get('revenue') or 0:,.2f} | "
            f"Margin: {p.get('margin_pct') or 0:.1f}% | "
            f"_{p.get('recommendation', '')}_"
        )

    lines += ["", "## 🧹 Top 5 — REDUCE (Class C)"]
    for p in report.get("reduce", []):
        lines.append(
            f"- **{p.get('full_name', '?')}** | "
            f"Rev: R$ {p.get('revenue') or 0:,.2f} | "
            f"_{p.get('recommendation', '')}_"
        )

    urgent = report.get("urgent_restock", [])
    if urgent:
        lines += ["", "## 🚨 Urgent Restock (Class A — low stock)"]
        for p in urgent:
            lines.append(f"- **{p.get('full_name', '?')}** | Qtd: {p.get('qty_sold') or 0:.0f}")

    exits = report.get("exit_candidates", [])
    if exits:
        lines += ["", "## ⚰️  Exit Candidates (Class C — low revenue)"]
        for p in exits:
            lines.append(
                f"- **{p.get('full_name', '?')}** | Rev: R$ {p.get('revenue') or 0:,.2f}"
            )

    return "\n".join(lines)


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_abc_report(
    df: pd.DataFrame,
    save_path: Path | None = None,
    save_md: bool = True,
) -> dict[str, Any]:
    """
    Generate the ABC weekly decision report from an enriched product DataFrame.

    Parameters
    ----------
    df        : pd.DataFrame — enriched with core/decision_engine.enrich_with_decisions().
                If decision columns are missing, they are computed automatically.
    save_path : Path | None — JSON output path. Defaults to data/outputs/abc_weekly_report.json
    save_md   : bool — also write a Markdown summary (default True)

    Returns
    -------
    dict — full report structure (identical to what is written to JSON).

    Edge cases
    ----------
    - Empty DataFrame     → returns minimal report with empty sections
    - Missing abc_class   → returns report with warning in metadata
    - Missing dec columns → auto-enriches via enrich_with_decisions()
    - NaN values          → replaced with None before JSON serialisation
    """
    out_path = Path(save_path) if save_path else _DEFAULT_OUT
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if df.empty:
        logger.warning("generate_abc_report: received empty DataFrame.")
        return {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": "empty",
            },
            "scale": [], "optimize": [], "reduce": [],
            "urgent_restock": [], "exit_candidates": [],
        }

    data = df.copy()

    # Auto-enrich if decision columns are absent
    decision_cols = {"action_tag", "recommendation", "priority"}
    if not decision_cols.issubset(set(data.columns)):
        logger.info("generate_abc_report: decision columns missing — running enrich_with_decisions().")
        data = enrich_with_decisions(data)

    # Thresholds (for metadata transparency)
    thr = compute_default_thresholds(data)

    report: dict[str, Any] = {
        "metadata": {
            "generated_at":   datetime.now(timezone.utc).isoformat(),
            "total_products": int(len(data)),
            "distribution":   _class_distribution(data),
            "thresholds":     {k: round(v, 2) for k, v in thr.items()},
            "status":         "ok",
        },
        "scale":    _class_section(data, "A", sort_col="revenue", ascending=False),
        "optimize": _class_section(data, "B", sort_col="revenue", ascending=False),
        "reduce":   _class_section(data, "C", sort_col="revenue", ascending=True),
        "urgent_restock":  _recommendation_section(data, "RESTOCK URGENTLY"),
        "exit_candidates": _recommendation_section(data, "CONSIDER DISCONTINUATION"),
    }

    # ── Save JSON ──────────────────────────────────────────────────────────────
    try:
        json_str = json.dumps(report, ensure_ascii=False, indent=2, default=str)
        out_path.write_text(json_str, encoding="utf-8")
        logger.info("generate_abc_report: JSON saved → %s", out_path)
    except Exception as exc:
        logger.error("generate_abc_report: failed to save JSON — %s", exc)

    # ── Optional Markdown ──────────────────────────────────────────────────────
    if save_md:
        try:
            md_text = _markdown_summary(report)
            _DEFAULT_MD.write_text(md_text, encoding="utf-8")
            logger.info("generate_abc_report: Markdown saved → %s", _DEFAULT_MD)
        except Exception as exc:
            logger.warning("generate_abc_report: Markdown save failed (non-critical) — %s", exc)

    return report
