# FulôFiló Analytics Pro (Apple-Tailored, Local-First)

Dashboard and reporting stack for FulôFiló, optimized for macOS on Apple Silicon.

The canonical daily operation in production is the dashboard track: Streamlit + DuckDB + Parquet, fed by an Excel master workbook.

## Canonical Operating Model

- Source of truth: `data/excel/FuloFilo_Master.xlsx`
- Editor: Excel (operator edits the workbook directly)
- Sync command: `bash scripts/sync_excel.sh`
- Read model: `data/parquet/*.parquet` and `data/fulofilo.duckdb`
- Dashboard behavior: read-only for source-owned business datasets

Excel master sheets (input):
- `Catalog` — product definitions, costs, prices
- `Inventory` — current stock levels
- `DailySales` — transaction history
- `Cashflow` — revenue and expense entries
- `CategoryOverrides` — category assignments and confidence
- `Meta` — schema version and workbook metadata

## Quick Start (Dashboard)

```bash
cd /Users/giovannini_nuovo/Documents/GitHub/FuloFilo
uv sync
bash scripts/sync_excel.sh
bash scripts/launch_app.sh
```

App URL: `http://127.0.0.1:8501`

GUI launcher (canonical Finder path): double-click `FuloFilo.command`

## Daily Operations

1. Open the Excel master: `open data/excel/FuloFilo_Master.xlsx`
2. Edit the relevant sheet (Catalog, Inventory, DailySales, etc.).
3. Run sync:
   `bash scripts/sync_excel.sh`
4. Open dashboard and review:
   `bash scripts/launch_app.sh` or `FuloFilo.command`
5. Optional report artifact:
   `python3 excel/build_report.py` (or use page `06_export_excel`)

## Bootstrap (first time)

If you don't have the Excel master yet, generate it from existing CSV data:

```bash
uv run python scripts/bootstrap_excel_master.py
```

## Validation Policies

`scripts/sync_excel.py` enforces:
- required columns for all master sheets
- SKU uniqueness in Catalog
- referential integrity (Inventory, DailySales, CategoryOverrides SKUs must exist in Catalog)
- non-negativity for prices, costs, and quantities
- Sales total reconciliation (Total vs Quantity * Unit_Price)
- KPI-impact reporting for blank `sku` in daily sales

Policy modes:
- `balanced` (default): blank SKU is reported as warning with KPI-impact count
- `strict`: KPI-impact rows with blank SKU become sync errors

Strict mode example:
```bash
bash scripts/sync_excel.sh --sku-policy strict
```

## Legacy CSV Pipeline

The previous Numbers/CSV workflow (`scripts/sync_native_sources.sh`) is still available
during the migration period. It reads from `data/raw/*_master.csv` files.

## Out of Scope for Dashboard Runbook

- `cf-worker/` is deployment infrastructure and not required for local dashboard operations.
