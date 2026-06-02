# FulôFiló AI Retail Operations Terminal

Official institutional retail-intelligence dashboard for FulôFiló, optimized for macOS on Apple Silicon.

The canonical daily operation in production is the terminal track: Excel master workbook → sync pipeline → Parquet/DuckDB read models → Streamlit retail operations terminal.

## Canonical Operating Model

- Source of truth: `data/excel/FuloFilo_Master.xlsx`
- Editor: Excel (operator edits the workbook directly)
- Sync command: `bash scripts/sync_excel.sh`
- Read model: `data/parquet/*.parquet` and `data/fulofilo.duckdb`
- Official dashboard: `app/app.py` — FulôFiló AI Retail Operations Terminal
- Dashboard behavior: read-only for source-owned business datasets

Excel master sheets (input):
- `Catalog` — product definitions, costs, prices
- `Inventory` — current stock levels
- `DailySales` — transaction history
- `Cashflow` — revenue and expense entries
- `CategoryOverrides` — category assignments and confidence
- `Meta` — schema version and workbook metadata

## Quick Start (Official Dashboard)

```bash
git clone https://github.com/AUTOGIO/fulofilo-analytics.git
cd fulofilo-analytics
uv sync
bash scripts/setup_automations.sh   # Loyverse + Rede (first time)
bash scripts/sync_excel.sh
bash scripts/launch_app.sh
```

Local sales automations (Loyverse exports, Rede portal downloads) are bundled under [`automations/`](automations/README.md).

App URL: `http://127.0.0.1:8501`

GUI launcher (canonical Finder path): double-click `FuloFilo.command`

## n8n External Orchestration Layer

Use n8n only as control plane. Keep business logic in this repository.

### What n8n can orchestrate

- schedule and trigger automation runs
- call local webhook/CLI entrypoints
- coordinate retries and workflow order

### What must stay in Python business logic

- data integrity rules from `scripts/sync_excel.py`
- inventory/reorder calculations from `app/utils/reorder_engine.py`
- report generation from `excel/build_report.py` and `reports/weekly_report.py`

### Automation entrypoints (n8n-safe)

```bash
cd fulofilo-analytics
make automation-refresh-dashboard-data
make automation-sync-excel-master
make automation-generate-replenishment-alerts
make automation-export-reports
make automation-validate-data-integrity
```

Direct CLI equivalent:

```bash
.venv/bin/python3 scripts/automation_cli.py refresh-dashboard-data
```

### Start n8n locally (Docker)

```bash
cd fulofilo-analytics
docker compose -f docker-compose.n8n.yml up -d
```

n8n UI: [http://localhost:5678](http://localhost:5678)

### Trigger project automations from n8n

For Dockerized n8n, run local webhook bridge on macOS host:

```bash
cd fulofilo-analytics
export FULOFILO_AUTOMATION_TOKEN="change-this-token"
make automation-webhook
```

Then use n8n HTTP Request nodes targeting:

- `GET http://host.docker.internal:8787/health`
- `POST http://host.docker.internal:8787/run`

Sample body:

```json
{
  "action": "refresh-dashboard-data",
  "idempotency_key": "n8n-exec-123:refresh"
}
```

Full sample workflow JSON:
`docs/n8n/fulofilo_orchestration_workflow.json`

## Daily Operations

1. Register daily sales manually in page `04_daily_ops`.
2. Run the automatic routine:
   `make automation-run-daily`
3. Open dashboard and review:
   `bash scripts/launch_app.sh` or `FuloFilo.command`

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

Workbook backups must use this operator-visible convention:
`data/excel/backups/FuloFilo_Master_YYYYMMDD_HHMMSS.xlsx`

## Legacy Notice

Historical CSV/JSON files are retained for audit history only.
They are not part of the active operational workflow.

## Out of Scope for Dashboard Runbook

- `cf-worker/` is deployment infrastructure and not required for local dashboard operations.
