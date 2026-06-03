# FulôFiló Docs

This docs set reflects the current Excel-first + n8n-orchestrated operating model.

## Canonical Runtime

```bash
git clone https://github.com/AUTOGIO/fulofilo-analytics.git
cd fulofilo-analytics
uv sync
bash scripts/setup_automations.sh
bash scripts/sync_excel.sh
bash scripts/launch_app.sh
```

Bundled Loyverse/Rede automations live under [`automations/`](../automations/README.md) (no separate repos required).

Loyverse and Rede automations (setup, daily use, troubleshooting): **[AUTOMATIONS_USER_GUIDE.md](AUTOMATIONS_USER_GUIDE.md)**.

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

- [`docs/n8n/README.md`](n8n/README.md)
- [`docs/n8n/fulofilo_orchestration_workflow.json`](n8n/fulofilo_orchestration_workflow.json)
- [`docs/USER_GUIDE.md`](USER_GUIDE.md)
- [`docs/AUTOMATIONS_USER_GUIDE.md`](AUTOMATIONS_USER_GUIDE.md)
- [`docs/CODEX_OPERATOR_SETUP_PROMPT.md`](CODEX_OPERATOR_SETUP_PROMPT.md) — Codex: clone, install, open dashboards + guided tour

## Legacy Notice

Historical CSV/JSON files remain for audit traceability.
They are not active operational write targets.
