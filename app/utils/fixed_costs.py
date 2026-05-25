"""
FulôFiló — Fixed Costs Loader
==============================
Loads custos_fixos.txt (JSON) and returns a Polars DataFrame + summary.
No DuckDB dependency — fixed costs are static monthly data.
"""

import json
from pathlib import Path
import polars as pl

_ROOT = Path(__file__).resolve().parent.parent.parent
_CANDIDATE_SOURCES = (
    _ROOT / "data" / "raw" / "costs" / "custos_fixos.txt",
    _ROOT / "data" / "raw" / "custos_fixos" / "custos_fixos.txt",
)


def _resolve_source() -> Path:
    for path in _CANDIDATE_SOURCES:
        if path.exists():
            return path
    raise FileNotFoundError(
        "Fixed costs source not found. Expected one of: "
        + ", ".join(str(p) for p in _CANDIDATE_SOURCES)
    )


def load_fixed_costs() -> tuple[pl.DataFrame, float]:
    """
    Returns:
        df      — Polars DataFrame with columns [categoria, item, valor_mensal_brl]
        total   — float, total monthly fixed cost
    """
    source = _resolve_source()
    data = json.loads(source.read_text(encoding="utf-8"))
    df = pl.DataFrame(data["custos_fixos"])
    total = float(data["total_mensal_brl"])
    return df, total
