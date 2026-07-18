"""Season indices and tourist-season overlays."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
SEASONS_CONFIG = ROOT / "config" / "tourist_seasons.yaml"


def load_tourist_config() -> dict[str, Any]:
    if not SEASONS_CONFIG.exists():
        return {"high_season_months": [12, 1, 2, 7], "multipliers": {"high": 1.25, "low": 0.85}}
    return yaml.safe_load(SEASONS_CONFIG.read_text(encoding="utf-8")) or {}


def compute_season_index(conn) -> pl.DataFrame:
    """Month-of-year index per category: avg(month) / avg(all)."""
    try:
        df = conn.execute("""
            SELECT
                p.category,
                CAST(strftime(CAST(s.Date AS DATE), '%m') AS INTEGER) AS month_num,
                SUM(CAST(s.Quantity AS DOUBLE)) AS units
            FROM sales s
            JOIN products p ON s.sku = p.sku OR lower(s.Product) = lower(p.full_name)
            GROUP BY 1, 2
        """).pl()
    except Exception:
        return pl.DataFrame()

    if df.is_empty():
        return df

    totals = df.group_by("category").agg(pl.col("units").mean().alias("avg_units"))
    return (
        df.join(totals, on="category")
        .with_columns((pl.col("units") / pl.col("avg_units").replace(0, 1)).alias("season_index"))
        .select("category", "month_num", "season_index", "units")
    )


def tourist_multiplier(month_num: int, config: dict[str, Any] | None = None) -> float:
    cfg = config or load_tourist_config()
    high = set(cfg.get("high_season_months", [12, 1, 2, 7]))
    mult = cfg.get("multipliers", {})
    if month_num in high:
        return float(mult.get("high", 1.25))
    return float(mult.get("low", 0.85))


def project_category_units(
    daily_units: float,
    horizon_days: int,
    month_num: int,
    season_index: float = 1.0,
) -> dict[str, float]:
    """Simple seasonal projection."""
    cfg = load_tourist_config()
    tourist = tourist_multiplier(month_num, cfg)
    adjusted = daily_units * season_index * tourist
    point = adjusted * horizon_days
    return {
        "forecast_units": round(point, 1),
        "lower_bound": round(point * 0.75, 1),
        "upper_bound": round(point * 1.35, 1),
        "season_index": round(season_index, 3),
        "tourist_multiplier": tourist,
    }
