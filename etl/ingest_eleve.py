"""
FulôFiló — Eleve Vendas Data Ingestion
=======================================
Converts raw exports from Eleve Vendas (CSV/JSON) into optimized Parquet files.

Expected input format (dashboard_data.json):
  {
    "revenue_report":  [{"item": str, "quantity": float, "revenue": float}],
    "quantity_report": [{"cost": float, "item": str, "profit": float, "quantity": float, "revenue": float}],
    "profit_report":   [{"code": str, "item": str, "quantity": float, "total": float}]
  }

Usage:
    python etl/ingest_eleve.py
    python etl/ingest_eleve.py --dry-run      # validate without writing
    python etl/ingest_eleve.py --source path/to/custom.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import polars as pl

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
RAW  = BASE / "data" / "raw"
OUT  = BASE / "data" / "parquet"
LOGS = BASE / "logs"

LOGS.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOGS / "ingest.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("ingest_eleve")

# ── Required JSON keys ────────────────────────────────────────────────────────
REQUIRED_KEYS = {"revenue_report", "quantity_report", "profit_report"}
SCHEMA_CHECKS = {
    "revenue_report":  {"item", "quantity", "revenue"},
    "quantity_report": {"cost", "item", "profit", "quantity", "revenue"},
    "profit_report":   {"code", "item", "quantity", "total"},
}


def _validate_source(source_path: Path) -> dict:
    """Load and validate the JSON source file. Exits with code 1 on failure."""
    if not source_path.exists():
        log.error("Input file not found: %s", source_path)
        log.error("  → Drop your Eleve Vendas export here: %s", RAW)
        sys.exit(1)

    if source_path.suffix.lower() != ".json":
        log.error("Expected .json file, got: %s", source_path.suffix)
        sys.exit(1)

    try:
        with open(source_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        log.error("Invalid JSON in %s: %s", source_path, exc)
        sys.exit(1)

    # Check top-level keys
    missing_keys = REQUIRED_KEYS - set(data.keys())
    if missing_keys:
        log.error("Missing required keys in JSON: %s", missing_keys)
        log.error("  → Found keys: %s", set(data.keys()))
        sys.exit(1)

    # Check row schemas
    for table, required_cols in SCHEMA_CHECKS.items():
        rows = data.get(table, [])
        if not rows:
            log.warning("Table '%s' is empty — this may be expected.", table)
            continue
        actual_cols = set(rows[0].keys())
        missing_cols = required_cols - actual_cols
        if missing_cols:
            log.error("Table '%s' missing columns: %s", table, missing_cols)
            sys.exit(1)
        log.info("  ✓ %s: %d rows, cols %s", table, len(rows), sorted(actual_cols))

    return data


def _write_parquet(df: pl.DataFrame, name: str, dry_run: bool) -> None:
    path = OUT / f"{name}.parquet"
    if dry_run:
        log.info("  [DRY RUN] Would write %d rows → %s", df.shape[0], path)
    else:
        df.write_parquet(path)
        log.info("  ✅ %s: %d rows → %s", name, df.shape[0], path)


def ingest(source_path: Path | None = None, dry_run: bool = False) -> None:
    source = source_path or (RAW / "dashboard_data.json")
    log.info("=" * 60)
    log.info("FulôFiló ETL — Eleve Vendas ingestion started")
    log.info("  source  : %s", source)
    log.info("  dry_run : %s", dry_run)
    log.info("=" * 60)

    data = _validate_source(source)

    # 1. Report tables
    revenue  = pl.DataFrame(data["revenue_report"])
    quantity = pl.DataFrame(data["quantity_report"])
    profit   = pl.DataFrame(data["profit_report"])
    log.info("Loaded: %d revenue, %d quantity, %d profit rows",
             revenue.shape[0], quantity.shape[0], profit.shape[0])

    _write_parquet(revenue,  "revenue_report",  dry_run)
    _write_parquet(quantity, "quantity_report", dry_run)
    _write_parquet(profit,   "profit_report",   dry_run)

    # 2. Empty skeleton parquets (templates) — only if not already populated
    for skeleton_name, schema in [
        ("daily_sales", {"Date": pl.Utf8, "Product": pl.Utf8, "Quantity": pl.Float64,
                          "Unit_Price": pl.Float64, "Total": pl.Float64,
                          "Payment_Method": pl.Utf8, "Source": pl.Utf8}),
        ("cashflow",    {"Date": pl.Utf8, "Type": pl.Utf8, "Category": pl.Utf8,
                          "Description": pl.Utf8, "Amount": pl.Float64,
                          "Payment_Method": pl.Utf8}),
    ]:
        existing = OUT / f"{skeleton_name}.parquet"
        if not existing.exists() or pl.read_parquet(existing).is_empty():
            _write_parquet(pl.DataFrame(schema=schema), skeleton_name, dry_run)
        else:
            log.info("  → %s already populated, skipping skeleton write", skeleton_name)

    # 3. Inventory — rebuild from products if available
    products_path = OUT / "products.parquet"
    if products_path.exists():
        products = pl.read_parquet(products_path)
        inv_path = OUT / "inventory.parquet"
        if not inv_path.exists() or pl.read_parquet(inv_path)["current_stock"].sum() == 0:
            inventory = products.select([
                pl.col("sku"),
                pl.col("full_name").alias("product"),
                pl.col("category"),
                pl.lit(0).cast(pl.Int32).alias("current_stock"),
                pl.col("min_stock"),
                pl.col("reorder_qty"),
                pl.lit("").alias("supplier"),
                pl.lit(7).cast(pl.Int32).alias("lead_time_days"),
                pl.lit("").alias("notes"),
            ])
            _write_parquet(inventory, "inventory", dry_run)
        else:
            log.info("  → inventory.parquet has stock counts, skipping rebuild")
    else:
        log.warning("products.parquet not found — run build_catalog.py first")

    log.info("Ingestion %s.", "validated (dry-run, no writes)" if dry_run else "complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FulôFiló — Eleve Vendas ingestion")
    parser.add_argument("--source", type=Path, default=None,
                        help="Path to Eleve Vendas JSON export (default: data/raw/dashboard_data.json)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate input without writing any Parquet files")
    args = parser.parse_args()
    ingest(source_path=args.source, dry_run=args.dry_run)
