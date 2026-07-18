"""What-if scenario simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from core.procurement.lead_time import COVERAGE_DAYS, get_reorder_df


@dataclass
class ScenarioParams:
    demand_multiplier: float = 1.0
    lead_time_days_delta: int = 0
    coverage_days: int = COVERAGE_DAYS
    unit_cost_delta_pct: float = 0.0
    exclude_categories: list[str] = field(default_factory=list)


def run_scenario(conn, params: ScenarioParams) -> dict[str, Any]:
    """Compare baseline reorder metrics vs scenario-adjusted values."""
    baseline = get_reorder_df(conn)
    if baseline.empty:
        return {"baseline": baseline, "scenario": baseline, "summary": {}}

    scenario = baseline.copy()
    if params.exclude_categories:
        scenario = scenario[~scenario["category"].isin(params.exclude_categories)]

    scenario["daily_rate"] = scenario["daily_rate"] * params.demand_multiplier
    scenario["lead_time"] = (scenario["lead_time"] + params.lead_time_days_delta).clip(lower=1)
    scenario["buffer"] = scenario["buffer"]  # keep dynamic buffer from baseline
    scenario["alert_threshold"] = scenario["lead_time"] + scenario["buffer"]

    stock = scenario["current_stock"].astype(float)
    rate = scenario["daily_rate"].astype(float)
    scenario["days_remaining"] = (stock / rate.replace(0, float("nan"))).round(0).fillna(9999)
    need = (rate * params.coverage_days - stock).clip(lower=0)
    scenario["suggested_qty"] = need.apply(lambda x: int(__import__("math").ceil(x)))

    unit_cost = scenario["unit_cost"].astype(float) * (1 + params.unit_cost_delta_pct / 100)
    scenario["inventory_value_brl"] = (stock * unit_cost).round(2)
    scenario["projected_lost_profit_brl"] = (
        (scenario["alert_threshold"] - scenario["days_remaining"]).clip(lower=0)
        * rate
        * scenario["unit_profit"].astype(float)
    ).round(2)

    baseline_at_risk = int((baseline["days_remaining"] <= baseline["alert_threshold"]).sum())
    scenario_at_risk = int((scenario["days_remaining"] <= scenario["alert_threshold"]).sum())

    summary = {
        "baseline_at_risk_skus": baseline_at_risk,
        "scenario_at_risk_skus": scenario_at_risk,
        "delta_at_risk": scenario_at_risk - baseline_at_risk,
        "baseline_total_suggested_qty": int(baseline["suggested_qty"].sum()),
        "scenario_total_suggested_qty": int(scenario["suggested_qty"].sum()),
        "baseline_inventory_value_brl": float(baseline.get("unit_cost", pd.Series([0])).astype(float).mul(
            baseline["current_stock"].astype(float)
        ).sum()),
        "scenario_inventory_value_brl": float(scenario["inventory_value_brl"].sum()),
    }

    return {"baseline": baseline, "scenario": scenario, "summary": summary, "params": params}
