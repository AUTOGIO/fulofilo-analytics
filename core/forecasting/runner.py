"""Batch forecast runner for automation artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl

from core.forecasting.models import forecast_categories, forecast_skus
from core.forecasting.seasonal import compute_season_index, project_category_units, tourist_multiplier
from core.forecasting.series import build_category_series, build_sku_series

ROOT = Path(__file__).resolve().parent.parent.parent


def run_forecasts(conn, *, category_horizon: int = 7, sku_horizon: int = 30) -> dict[str, Any]:
    cat_series = build_category_series(conn, grain="day")
    sku_series = build_sku_series(conn, grain="day")

    # Class A SKUs only for SKU-level forecasts
    try:
        class_a = conn.execute("SELECT sku FROM products WHERE abc_class = 'A'").df()["sku"].tolist()
    except Exception:
        class_a = []
    if class_a:
        sku_series = sku_series.filter(pl.col("entity").is_in(class_a))

    category_forecasts = forecast_categories(cat_series, horizon_days=category_horizon)
    sku_forecasts = forecast_skus(sku_series, horizon_days=sku_horizon) if not sku_series.is_empty() else []

    season_idx = compute_season_index(conn)
    month_num = datetime.now().month
    tourist = tourist_multiplier(month_num)

    for fc in category_forecasts:
        entity = fc["entity"]
        idx_row = season_idx.filter(pl.col("category") == entity, pl.col("month_num") == month_num)
        idx = float(idx_row["season_index"][0]) if not idx_row.is_empty() else 1.0
        daily = float(fc.get("daily_rate") or (fc["forecast_units"] / max(category_horizon, 1)))
        seasonal = project_category_units(daily, category_horizon, month_num, idx)
        fc.update(seasonal)
        fc["tourist_multiplier"] = tourist

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "category_forecasts": category_forecasts,
        "sku_forecasts": sku_forecasts,
        "category_horizon_days": category_horizon,
        "sku_horizon_days": sku_horizon,
    }


def save_forecast_artifacts(conn, out_dir: Path | None = None) -> dict[str, str]:
    out = out_dir or (ROOT / "data" / "outputs" / "forecasts")
    out.mkdir(parents=True, exist_ok=True)
    payload = run_forecasts(conn)
    cat_path = out / "category_7d.json"
    sku_path = out / "sku_30d.json"
    cat_path.write_text(
        json.dumps(
            {"generated_at": payload["generated_at"], "forecasts": payload["category_forecasts"]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    sku_path.write_text(
        json.dumps(
            {"generated_at": payload["generated_at"], "forecasts": payload["sku_forecasts"]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"category_json": str(cat_path), "sku_json": str(sku_path)}
