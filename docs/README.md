# FulôFiló Docs

This docs set reflects the current Excel-first + n8n-orchestrated operating model.

## Canonical Runtime

```bash
cd /Users/eduardofgiovannini/Documents/GitHub/fulofilo-analytics
uv sync
bash scripts/sync_excel.sh
bash scripts/launch_app.sh
```

Canonical source of truth:

- `data/excel/FuloFilo_Master.xlsx`

Generated artifacts (read models / reports):

- `data/parquet/*.parquet`
- `data/fulofilo.duckdb`
- `data/raw/catalogs/product_catalog.csv`
- `excel/FuloFilo_Report_*.xlsx`

## External Orchestration (n8n)

n8n is the external control plane only (scheduling, triggers, ordering, retries).
Business logic remains in Python code inside this repository.

Primary references:

- `/Users/eduardofgiovannini/Documents/GitHub/fulofilo-analytics/docs/n8n/README.md`
- `/Users/eduardofgiovannini/Documents/GitHub/fulofilo-analytics/docs/USER_GUIDE.md`

## Legacy Notice

Historical CSV/JSON files remain for audit traceability.
They are not active operational write targets.
