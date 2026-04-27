# FulôFiló Analytics Pro — User Guide

_Last updated: 2026-04-27_

## 1. What the operator should treat as real data

Use only:

- `data/excel/FuloFilo_Master.xlsx`

Do not use as operational sources:

- `data/parquet/*.parquet`
- `data/fulofilo.duckdb`
- `data/raw/product_catalog.csv`
- `excel/FuloFilo_Report_*.xlsx`
- `data/raw/daily_sales_TEMPLATE.csv`
- `data/raw/product_catalog_categorized.csv`

## 2. Daily workflow

1. Open `data/excel/FuloFilo_Master.xlsx`.
2. Update `Catalog`, `Inventory`, `DailySales`, `Cashflow`, or `CategoryOverrides`.
3. Run `bash scripts/sync_excel.sh`.
4. Open or refresh the dashboard with `bash scripts/launch_app.sh`.
5. If needed, generate a report with `./.venv/bin/python3 excel/build_report.py`.

## 3. What the dashboard now writes back

- `Operações Diárias` appends new sales to `DailySales`
- `Categorias` writes manual overrides to `CategoryOverrides`
- `Estoque` updates `Inventory` and appends `data/logs/stock_audit.csv`

All of those write-backs target the Excel master first and then trigger canonical sync.

## 4. Safety warnings you may see

The app warns when:

- the workbook still contains only the bootstrap placeholder SKU
- `Inventory` is empty or still only contains the placeholder row
- `DailySales` has zero rows
- `Cashflow` has zero rows
- sync succeeded but the generated data is not healthy for production decisions

If you see those warnings, do not trust KPI totals yet. Load real business rows into the Excel master and sync again.

## 5. Production onboarding checklist

1. Back up the workbook first.
   Backup convention: `data/excel/backups/FuloFilo_Master_YYYYMMDD_HHMMSS.xlsx`
   If two backups happen in the same second, the system appends `_01`, `_02`, and so on.
2. Prepare source data externally before touching the workbook.
3. Confirm each destination sheet still has the canonical headers.
4. Replace the bootstrap content sheet by sheet:
   `Catalog`: paste real SKUs, names, categories, costs, prices, minimum stock, and reorder quantities.
   `Inventory`: paste real stock rows for the same SKUs used in `Catalog`.
   `DailySales`: paste real transaction history with `Date`, `sku`, `Product`, `Quantity`, `Unit_Price`, `Total`, `Payment_Method`, `Source`.
   `Cashflow`: paste real revenue and expense rows.
   `CategoryOverrides`: add only manual category corrections; this sheet may remain empty if not needed.
   `Meta`: keep at least `schema_version` and `workbook`.
5. Run `bash scripts/sync_excel.sh`.
6. Review `data/excel/source_sync_status.json`.
7. Run `./.venv/bin/python3 -m pytest -q tests/test_pipeline.py`.
8. Open the dashboard with `bash scripts/launch_app.sh`.
9. Confirm KPIs are populated and the sidebar no longer says the system is not production-ready.

Manual backup example:

```bash
mkdir -p data/excel/backups
cp data/excel/FuloFilo_Master.xlsx "data/excel/backups/FuloFilo_Master_$(date +%Y%m%d_%H%M%S).xlsx"
```

## 6. Legacy files

Historical raw CSV and JSON files remain in the repository for evidence and migration history. They are not the active workflow and should not be edited as part of normal operations.

`scripts/refresh_data.sh` is archived and intentionally disabled.

## 7. Real Migration Day Checklist

1. Back up `data/excel/FuloFilo_Master.xlsx` to `data/excel/backups/FuloFilo_Master_YYYYMMDD_HHMMSS.xlsx`.
   If the timestamp already exists, keep the auto-appended suffix such as `_01`.
2. Import real business data into `Catalog`, `Inventory`, `DailySales`, `Cashflow`, and optional `CategoryOverrides`.
3. Preserve `Meta` keys `schema_version` and `workbook`.
4. Run `bash scripts/sync_excel.sh`.
5. Review `data/excel/source_sync_status.json` and confirm `healthy_production_data` is `true`.
6. Run `./.venv/bin/python3 -m pytest -q tests/test_pipeline.py`.
7. Run an operator smoke test in the dashboard:
   confirm KPIs are populated, search products, register one sale if appropriate, and verify stock/cash views are populated.
8. Generate a fresh report with `./.venv/bin/python3 excel/build_report.py`.
9. If anything looks wrong, roll back by restoring the latest backup workbook and re-running `bash scripts/sync_excel.sh`.
