"""
FulôFiló — Fixed Costs Loader
==============================
Loads custos_fixos.txt (JSON) and returns a Polars DataFrame + summary.
No DuckDB dependency — fixed costs are static monthly data.
"""

import json
from pathlib import Path
import polars as pl

_SOURCE = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "custos_fixos" / "custos_fixos.txt"


def load_fixed_costs() -> tuple[pl.DataFrame, float]:
    """
    Returns:
        df      — Polars DataFrame with columns [categoria, item, valor_mensal_brl]
        total   — float, total monthly fixed cost
    """
    data = json.loads(_SOURCE.read_text(encoding="utf-8"))
    df = pl.DataFrame(data["custos_fixos"])
    total = float(data["total_mensal_brl"])
    return df, total
