# FulôFiló AI

Local-first retail analytics for FulôFiló on macOS Apple Silicon.

## Canonical Architecture

```text
data/excel/FuloFilo_Master.xlsx
  -> bash scripts/sync_excel.sh
  -> data/parquet/*.parquet
  -> data/fulofilo.duckdb
  -> Streamlit dashboard
  -> .venv/bin/python3 excel/build_report.py
```

## Source of Truth

The only operational source of truth is:

- `data/excel/FuloFilo_Master.xlsx`

Primary sheets:

- `Catalog`
- `Inventory`
- `DailySales`
- `Cashflow`
- `CategoryOverrides`
- `Meta`

Do not treat these as source-of-truth:

- `data/parquet/*.parquet` — generated read models
- `data/fulofilo.duckdb` — generated query layer
- `data/raw/product_catalog.csv` — generated catalog export
- `excel/FuloFilo_Report_*.xlsx` — generated reports

Historical raw CSV and JSON files remain in the repository as archived evidence only.

## Quick Start

```bash
cd /Users/giovannini_nuovo/Documents/GitHub/FuloFilo
uv sync
bash scripts/sync_excel.sh
bash scripts/launch_app.sh
```

App URL: `http://127.0.0.1:8501`

## Daily Operation

1. Open `data/excel/FuloFilo_Master.xlsx`.
2. Update the relevant canonical sheet.
3. Run `bash scripts/sync_excel.sh`.
4. Launch or refresh the app with `bash scripts/launch_app.sh`.
5. Optionally generate a report with `./.venv/bin/python3 excel/build_report.py`.

## Production Onboarding Checklist

1. Back up the workbook first.
   Backup convention: `data/excel/backups/FuloFilo_Master_YYYYMMDD_HHMMSS.xlsx`
   If a backup already exists for that second, the system appends `_01`, `_02`, and so on.
2. Prepare source data outside the repo and confirm the canonical sheet columns before pasting.
3. Replace bootstrap rows in `Catalog` and `Inventory` with real business data.
4. Load real history into `DailySales` and `Cashflow`.
5. Add `CategoryOverrides` only where manual corrections are needed.
6. Confirm `Meta` still contains at least `schema_version` and `workbook`.
7. Run `bash scripts/sync_excel.sh`.
8. Review `data/excel/source_sync_status.json`.
9. Run `./.venv/bin/python3 -m pytest -q tests/test_pipeline.py`.
10. Open the dashboard and confirm KPIs are no longer empty.

Manual backup example:

```bash
mkdir -p data/excel/backups
cp data/excel/FuloFilo_Master.xlsx "data/excel/backups/FuloFilo_Master_$(date +%Y%m%d_%H%M%S).xlsx"
```

## Bootstrap Note

`uv run python scripts/bootstrap_excel_master.py` creates a starter workbook with a placeholder SKU so the first sync can run. That workbook is not healthy production data until real catalog and sales rows replace the bootstrap content.

## Validation

```bash
cd /Users/giovannini_nuovo/Documents/GitHub/FuloFilo
uv sync
bash scripts/sync_excel.sh
./.venv/bin/python3 -m pytest -q tests/test_pipeline.py
./.venv/bin/python3 excel/build_report.py
```

## Legacy Paths

- `scripts/refresh_data.sh` is archived and intentionally disabled.
- Deleted ETL paths such as `etl/build_catalog.py`, `etl/ingest_eleve.py`, and `scripts/sync_native_sources.sh` are not part of the active workflow.
