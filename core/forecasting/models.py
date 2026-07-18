"""Tiered forecasting models (rolling mean / WMA)."""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl


def _wma(values: list[float], weights: list[float] | None = None) -> float:
    if not values:
        return 0.0
    if weights is None:
        weights = list(range(1, len(values) + 1))
    w = np.array(weights[-len(values):], dtype=float)
    v = np.array(values, dtype=float)
    if w.sum() == 0:
        return float(v.mean()) if len(v) else 0.0
    return float(np.dot(v, w) / w.sum())


def _backtest_mape(actual: list[float], predicted: list[float]) -> float | None:
    pairs = [(a, p) for a, p in zip(actual, predicted) if a > 0]
    if not pairs:
        return None
    errors = [abs(a - p) / a for a, p in pairs]
    return round(float(np.mean(errors)) * 100, 1)


def forecast_entity(
    series: pl.DataFrame,
    entity: str,
    *,
    horizon_days: int = 7,
    holdout_periods: int = 4,
) -> dict[str, Any]:
    """Forecast units for one entity from a period-level series."""
    sub = series.filter(pl.col("entity") == entity).sort("period")
    if sub.is_empty():
        return {"entity": entity, "forecast_units": 0.0, "model_id": "none"}

    units = sub["units"].to_list()
    sale_days = len([u for u in units if u > 0])
    if sale_days < 2:
        daily = float(np.mean(units)) if units else 0.0
        return {
            "entity": entity,
            "forecast_units": round(daily * horizon_days, 1),
            "lower_bound": 0.0,
            "upper_bound": round(daily * horizon_days * 1.5, 1),
            "model_id": "sparse_mean",
            "mape_backtest": None,
            "horizon_days": horizon_days,
        }

    train = units[:-holdout_periods] if len(units) > holdout_periods else units
    test = units[-holdout_periods:] if len(units) > holdout_periods else []

    wma_rate = _wma(train[-14:])
    rolling_rate = float(np.mean(train[-7:])) if train else 0.0
    daily_rate = max(wma_rate, rolling_rate * 0.9)

    preds = [daily_rate] * len(test)
    mape = _backtest_mape(test, preds) if test else None

    point = daily_rate * horizon_days
    spread = max(point * 0.2, daily_rate * 2)
    return {
        "entity": entity,
        "forecast_units": round(point, 1),
        "lower_bound": round(max(0, point - spread), 1),
        "upper_bound": round(point + spread, 1),
        "daily_rate": round(daily_rate, 3),
        "model_id": "wma_ensemble",
        "mape_backtest": mape,
        "horizon_days": horizon_days,
    }


def forecast_categories(series: pl.DataFrame, horizon_days: int = 7) -> list[dict[str, Any]]:
    entities = series["entity"].unique().to_list() if not series.is_empty() else []
    return [forecast_entity(series, str(e), horizon_days=horizon_days) for e in entities]


def forecast_skus(series: pl.DataFrame, horizon_days: int = 30) -> list[dict[str, Any]]:
    return forecast_categories(series, horizon_days=horizon_days)
