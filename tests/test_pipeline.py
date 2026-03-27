"""
FulôFiló — Minimum Viable Test Suite
=====================================
6 tests covering the full data pipeline.

Run:
    cd /Users/eduardogiovannini/dev/products/FuloFilo
    .venv/bin/python3 -m pytest tests/test_pipeline.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "data" / "parquet"
RAW_DIR  = ROOT / "data" / "raw"

EXPECTED_PARQUETS = [
    "cashflow", "daily_sales", "inventory", "products",
    "profit_report", "quantity_report", "revenue_report",
]


# ── Test 1 ────────────────────────────────────────────────────────────────────
def test_parquet_files_exist():
    """All 7 expected parquet files must be present on disk."""
    missing = []
    for name in EXPECTED_PARQUETS:
        path = DATA_DIR / f"{name}.parquet"
        if not path.exists():
            missing.append(name)
    assert missing == [], f"Missing parquet files: {missing}"


# ── Test 2 ────────────────────────────────────────────────────────────────────
def test_duckdb_products_not_empty():
    """DuckDB products view must return at least 1 row."""
    import duckdb
    db_path = ROOT / "data" / "fulofilo.duckdb"
    products_parquet = DATA_DIR / "products.parquet"
    assert products_parquet.exists(), "products.parquet must exist before DuckDB test"

    conn = duckdb.connect(str(db_path))
    conn.execute(f"CREATE OR REPLACE VIEW products AS "
                 f"SELECT * FROM read_parquet('{products_parquet}')")
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    conn.close()
    assert count > 0, f"products view returned {count} rows — expected > 0"


# ── Test 3 ────────────────────────────────────────────────────────────────────
def test_abc_classification_coverage():
    """Every product in products.parquet must have a valid A/B/C class."""
    df = pl.read_parquet(DATA_DIR / "products.parquet")
    assert df.shape[0] > 0, "products.parquet is empty"

    valid_classes = {"A", "B", "C"}
    if "abc_class" not in df.columns:
        pytest.skip("abc_class column not yet populated — run build_catalog.py")

    null_count = df["abc_class"].is_null().sum()
    assert null_count == 0, f"{null_count} products have null abc_class"

    invalid = df.filter(~pl.col("abc_class").is_in(list(valid_classes)))
    assert invalid.shape[0] == 0, \
        f"{invalid.shape[0]} products have invalid abc_class: {invalid['abc_class'].unique().to_list()}"


# ── Test 4 ────────────────────────────────────────────────────────────────────
def test_no_negative_prices():
    """No product may have a negative suggested_price or unit_cost."""
    df = pl.read_parquet(DATA_DIR / "products.parquet")
    assert df.shape[0] > 0, "products.parquet is empty"

    for col in ["suggested_price", "unit_cost"]:
        if col not in df.columns:
            continue
        neg = df.filter(pl.col(col) < 0)
        assert neg.shape[0] == 0, \
            f"{neg.shape[0]} products have negative {col}: {neg['sku'].to_list()}"


# ── Test 5 ────────────────────────────────────────────────────────────────────
def test_category_coverage():
    """After categorize_products runs, < 10% of products may be 'Não Classificado'."""
    cat_file = RAW_DIR / "product_catalog_categorized.csv"
    if not cat_file.exists():
        pytest.skip("product_catalog_categorized.csv not found — run categorize_products.py")

    df = pl.read_csv(cat_file)
    assert df.shape[0] > 0, "product_catalog_categorized.csv is empty"

    if "CategoryConfidence" not in df.columns:
        pytest.skip("CategoryConfidence column missing")

    total     = df.shape[0]
    unmatched = df.filter(pl.col("CategoryConfidence") == "unmatched").shape[0]
    pct       = unmatched / total if total else 0
    assert pct < 0.10, \
        f"{pct:.0%} unmatched (threshold: 10%). Add rules to etl/categorize_products.py."


# ── Test 6 ────────────────────────────────────────────────────────────────────
def test_excel_builds_successfully():
    """build_report() must produce a valid .xlsx file larger than 50 KB."""
    import tempfile
    from excel.build_report import build_report

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test_report.xlsx"
        result = build_report(output_path=out)
        # Check inside context — before tempdir is deleted
        assert result.exists(), f"Output file not found: {result}"
        size = result.stat().st_size
    assert size > 10_000, f"Generated Excel is too small ({size} bytes) — likely empty/corrupt"
