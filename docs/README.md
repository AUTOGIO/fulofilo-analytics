# FulôFiló Docs

This documentation set describes the current Excel-first operating model only.

## Canonical Workflow

```bash
cd /Users/giovannini_nuovo/Documents/GitHub/FuloFilo
uv sync
bash scripts/sync_excel.sh
bash scripts/launch_app.sh
```

Canonical source of truth:

- `data/excel/FuloFilo_Master.xlsx`

Generated artifacts:

- `data/parquet/*.parquet`
- `data/fulofilo.duckdb`
- `data/raw/product_catalog.csv`
- `excel/FuloFilo_Report_*.xlsx`

These generated artifacts are read models or reports, not operational sources.

## Legacy Notice

Historical CSV and JSON files are kept for audit and migration history only.
They are not the active sync path.

Archived paths:

- `scripts/refresh_data.sh`
- deleted `etl/build_catalog.py`
- deleted `etl/ingest_eleve.py`
- deleted `scripts/sync_native_sources.sh`
