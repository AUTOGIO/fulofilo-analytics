# DELIVERABLE 1 — PROFESSIONAL REPORT

**FulôFiló Analytics**  
**Target environment:** macOS Apple Silicon, local-first

## Repository alignment

The repository is aligned to:

```text
data/excel/FuloFilo_Master.xlsx
  -> scripts/sync_excel.sh
  -> data/parquet/*.parquet
  -> data/fulofilo.duckdb
  -> Streamlit dashboard
  -> excel/FuloFilo_Report_*.xlsx
```

External orchestration layer:

```text
n8n (schedule/webhook/trigger)
  -> scripts/automation_cli.py
  -> existing Python business logic
```

## Active write targets

Operational writes are limited to:

- `Catalog`, `Inventory`, `DailySales`, `Cashflow`, `CategoryOverrides` in `data/excel/FuloFilo_Master.xlsx`
- `data/logs/stock_audit.csv` as append-only audit evidence for stock changes

## Generated artifacts

Generated read models:

- `data/parquet/*.parquet`
- `data/fulofilo.duckdb`
- `data/raw/catalogs/product_catalog.csv`

Generated reports:

- `excel/FuloFilo_Report_*.xlsx`
- `data/outputs/*.json` (alerts/reports)

These files support analytics and reporting but are not canonical write targets.

## Orchestration boundary

n8n is allowed to orchestrate:

- schedules
- triggers/webhooks
- retries
- action ordering

n8n is not allowed to:

- implement business rules
- mutate canonical workbook data directly
- replace validation logic in Python modules

## Operator guidance

1. Update `data/excel/FuloFilo_Master.xlsx`
2. Run `bash scripts/sync_excel.sh` (or call automation action)
3. Review dashboard
4. Optionally export reports
5. Run integrity validation before production decisions
