# DELIVERABLE 1 — PROFESSIONAL REPORT

**FulôFiló AI**  
**Target environment:** macOS Apple Silicon, local-first

## Repository alignment

The repository is now aligned to a single operational model:

```text
data/excel/FuloFilo_Master.xlsx
  -> scripts/sync_excel.sh
  -> data/parquet/*.parquet
  -> data/fulofilo.duckdb
  -> Streamlit dashboard
  -> excel/FuloFilo_Report_*.xlsx
```

## Active write targets

Operational writes are limited to:

- `Catalog`, `Inventory`, `DailySales`, `Cashflow`, `CategoryOverrides` in `data/excel/FuloFilo_Master.xlsx`
- `data/logs/stock_audit.csv` as append-only audit evidence for stock changes

## Generated artifacts

Generated read models:

- `data/parquet/*.parquet`
- `data/fulofilo.duckdb`
- `data/raw/product_catalog.csv`

Generated reports:

- `excel/FuloFilo_Report_*.xlsx`

These files support analytics and reporting but are not canonical write targets.

## Legacy and archived material

The repository still contains historical CSV and JSON files for audit traceability. They remain available for reference, but they are not part of the active operational pipeline.

Quarantined legacy paths:

- `scripts/refresh_data.sh`
- deleted `etl/build_catalog.py`
- deleted `etl/ingest_eleve.py`
- deleted `scripts/sync_native_sources.sh`

## Operator guidance

Use this sequence only:

1. Update `data/excel/FuloFilo_Master.xlsx`
2. Run `bash scripts/sync_excel.sh`
3. Review the dashboard
4. Optionally run `./.venv/bin/python3 excel/build_report.py`

If the sync warns about bootstrap placeholder data or zero daily sales, the generated outputs are structurally valid but not safe to treat as live production analytics.
