# FulôFiló AI
## Technical Documentation and Operator Manual

Version: 3.0  
Date: April 2026  
Target: macOS Apple Silicon, local-first

## 1. System Identity

FulôFiló AI is a local retail analytics system built around an Excel-first operational model:

- Excel master workbook in `data/excel/FuloFilo_Master.xlsx`
- Canonical sync in `scripts/sync_excel.py` and `scripts/sync_excel.sh`
- Generated Parquet read models in `data/parquet/`
- DuckDB analytical layer in `data/fulofilo.duckdb`
- Streamlit dashboard in `app/`
- Excel report export in `excel/build_report.py`

Legacy CSV/JSON workflows are archived and are not part of normal operations.

## 2. Source-of-Truth Contract

Canonical source:

- `data/excel/FuloFilo_Master.xlsx`

Canonical sheets:

- `Catalog`
- `Inventory`
- `DailySales`
- `Cashflow`
- `CategoryOverrides`
- `Meta`

Operational rules:

- All business edits must land in the Excel master.
- Dashboard write-back actions must update the Excel master first.
- `bash scripts/sync_excel.sh` must be run after workbook changes.
- Generated Parquet, DuckDB, CSV exports, and report workbooks are never operational write targets.

## 3. Data Flow

```text
data/excel/FuloFilo_Master.xlsx
  -> scripts/sync_excel.py
  -> data/parquet/*.parquet
  -> data/fulofilo.duckdb
  -> Streamlit dashboard
  -> excel/build_report.py
```

Write-back implemented in the app:

- Daily sales append to `DailySales`
- Category overrides upsert to `CategoryOverrides`
- Inventory adjustments update `Inventory`
- Stock mutations append to `data/logs/stock_audit.csv`
- Each write-back triggers canonical sync

### Automation lane (`sales_watcher`) vs manual Excel

- **Manual lane:** Edit `FuloFilo_Master.xlsx`, then run `bash scripts/sync_excel.sh`.
- **Automation lane:** Drop `item-sales-summary-*.csv` into `data/incoming/`. The watcher runs `etl/ingest.py`, merges matching rows into the workbook under an advisory lock file (`data/excel/FuloFilo_Master.xlsx.lock`), runs `bash scripts/sync_excel.sh` so Parquet/DuckDB match the workbook, then archives the CSV and may `git push`.

Streamlit write-back and `sales_watcher` both use the same `locked_workbook` helper so concurrent saves do not interleave. If another process holds the lock longer than the timeout, the waiter logs a clear error and skips the write.

**LaunchAgent:** After moving or cloning the repo, run `bash scripts/launchagent/install_saleswatch.sh` again so `~/Library/LaunchAgents/com.fulofilo.saleswatch.plist` points at the correct repo root and Python. Optional: `scripts/launchagent/saleswatch.local.env.example` → `saleswatch.local.env` for `FULOFILO_ROOT` / `SALESWATCH_PYTHON`.

## 4. Generated Artifact Classification

Source of truth:

- `data/excel/FuloFilo_Master.xlsx`

Generated read models:

- `data/parquet/products.parquet`
- `data/parquet/inventory.parquet`
- `data/parquet/daily_sales.parquet`
- `data/parquet/cashflow.parquet`
- `data/parquet/revenue_report.parquet`
- `data/parquet/quantity_report.parquet`
- `data/parquet/profit_report.parquet`
- `data/fulofilo.duckdb`
- `data/raw/product_catalog.csv`

Generated reports:

- `excel/FuloFilo_Report_*.xlsx`
- `data/outputs/alertas_reposicao.xlsx`

Archived legacy evidence:

- historical files under `data/raw/`
- `product_catalog_categorized.csv`
- `daily_sales_TEMPLATE.csv`
- legacy JSON exports

Archived evidence may be inspected, but it is not part of the canonical operational write path.

## 5. Canonical Commands

Sync:

```bash
bash scripts/sync_excel.sh
```

Launch app:

```bash
bash scripts/launch_app.sh
```

Run tests:

```bash
./.venv/bin/python3 -m pytest -q tests/test_pipeline.py
```

Build report:

```bash
./.venv/bin/python3 excel/build_report.py
```

## 6. Validation and Safety

`scripts/sync_excel.py` validates:

- required columns on all canonical sheets
- SKU referential integrity
- non-negative costs and prices
- sales total reconciliation
- placeholder/bootstrap workbook warnings
- zero-sales warnings when `DailySales` is empty
- zero-cashflow warnings when `Cashflow` is empty
- inventory readiness warnings when `Inventory` is empty or still placeholder-only
- optional warnings when `CategoryOverrides` is empty
- missing `Meta` key warnings for `schema_version` and `workbook`

Sync status is written to:

- `data/excel/source_sync_status.json`

Machine-readable readiness fields include:

- `healthy_production_data`
- `readiness_state`
- `placeholder_only`
- `catalog_rows`
- `catalog_real_rows`
- `inventory_rows`
- `inventory_placeholder_only`
- `daily_sales_rows`
- `cashflow_rows`
- `category_override_rows`
- `meta_present_keys`
- `meta_missing_keys`

If the workbook still contains only `00001 / Produto Exemplo`, or if `Inventory`, `DailySales`, or `Cashflow` are empty, the sync may succeed but the generated outputs are not healthy production data.

Workbook backup convention:

- `data/excel/backups/FuloFilo_Master_YYYYMMDD_HHMMSS.xlsx`
- when two backups fall in the same second, `_01`, `_02`, and so on are appended automatically

The app write-back helpers already use this convention before saving workbook mutations.

## 7. Legacy Path Quarantine

These are not active and must not be presented as canonical:

- `etl/build_catalog.py`
- `etl/ingest_eleve.py`
- `scripts/sync_native_sources.sh`
- `scripts/refresh_data.sh`

`scripts/refresh_data.sh` remains in the repository only as an archived stub that tells the operator to use the Excel-first flow.
