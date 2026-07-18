"""Tests for forecasting modules."""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.forecasting.models import forecast_entity
from core.forecasting.seasonal import project_category_units, tourist_multiplier


def test_forecast_entity_returns_bounds():
    series = pl.DataFrame({
        "period": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
        "entity": ["CatA"] * 4,
        "entity_type": ["category"] * 4,
        "units": [2.0, 3.0, 4.0, 5.0],
        "revenue": [10.0, 15.0, 20.0, 25.0],
    })
    out = forecast_entity(series, "CatA", horizon_days=7)
    assert out["forecast_units"] >= 0
    assert out["lower_bound"] <= out["upper_bound"]
    assert out["model_id"]


def test_seasonal_projection():
    proj = project_category_units(10.0, 7, month_num=1, season_index=1.2)
    assert proj["forecast_units"] > 0
    assert tourist_multiplier(1) >= 1.0
