"""Tests for what-if simulation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.simulation.scenarios import ScenarioParams


def test_scenario_params_defaults():
    p = ScenarioParams()
    assert p.demand_multiplier == 1.0
    assert p.coverage_days == 45
