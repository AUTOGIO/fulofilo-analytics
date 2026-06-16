# FulôFiló Docs

This docs set reflects the current Excel-first + n8n-orchestrated operating model.

**Canonical repo path:** `~/Documents/GitHub/fulofilo-analytics` (not `~/Developer/fulofilo-*`). Separate clones at `~/Developer/loyverse-data` and `~/Developer/rede-automation` are optional overrides; this repo bundles automations under [`automations/`](../automations/README.md).

See also the root [README.md](../README.md) for quick start, daily ops, and validation policies.

## Prerequisites

| Need | Required for |
|------|--------------|
| [`uv`](https://docs.astral.sh/uv/) + Python 3.12 | All paths (`uv sync`) |
| Excel master at `data/excel/FuloFilo_Master.xlsx` | Dashboard (or run `scripts/bootstrap_excel_master.py`) |
| Node.js + npm | Rede automation |
| Google Chrome | Loyverse CDP profile |
| Playwright Chromium | Both automations (installed by `setup_automations.sh`) |
| Docker (optional) | n8n local orchestration |

Detailed automation setup: [AUTOMATIONS_USER_GUIDE.md](AUTOMATIONS_USER_GUIDE.md) §2. Architecture and guardrails: [AGENTS.md](../AGENTS.md).

## Canonical Runtime

```bash
git clone https://github.com/AUTOGIO/fulofilo-analytics.git
cd ~/Documents/GitHub/fulofilo-analytics
uv sync
bash scripts/setup_automations.sh   # Loyverse + Rede (first time only)
bash scripts/sync_excel.sh
bash scripts/launch_app.sh
```

App URL: `http://127.0.0.1:8501`

Bundled Loyverse/Rede automations live under [`automations/`](../automations/README.md) (no separate repos required).

Loyverse and Rede automations (setup, daily use, troubleshooting): **[AUTOMATIONS_USER_GUIDE.md](AUTOMATIONS_USER_GUIDE.md)**.

## When to Re-sync

Run `bash scripts/sync_excel.sh` whenever the Excel master changes:

- After any edit to `data/excel/FuloFilo_Master.xlsx`
- After Loyverse/Rede automations write new sales data into the workbook
- Before launching the dashboard if Excel was edited since the last sync

Then refresh the browser — no app restart required.

For validation before commits or when checking data integrity:

```bash
bash scripts/sync_excel.sh --sku-policy strict
uv run pytest
```

## Source of Truth & Generated Artifacts

Canonical source of truth:

- `data/excel/FuloFilo_Master.xlsx`

Generated artifacts (read models / reports):

- `data/parquet/*.parquet`
- `data/fulofilo.duckdb`
- `data/raw/catalogs/product_catalog.csv`
- `excel/FuloFilo_Report_*.xlsx`

## Documentation Map

| Doc | Audience | Purpose |
|-----|----------|---------|
| [README.md](../README.md) | Operator + dev | Quick start, daily ops, n8n, validation |
| [AGENTS.md](../AGENTS.md) | AI agents / devs | Architecture, commands, guardrails |
| [docs/README.md](README.md) | All | Docs index (this file) |
| [USER_GUIDE.md](USER_GUIDE.md) | Operator | Dashboard usage |
| [AUTOMATIONS_USER_GUIDE.md](AUTOMATIONS_USER_GUIDE.md) | Operator | Loyverse + Rede setup |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Analyst | Schema reference |
| [automations/README.md](../automations/README.md) | Dev | Bundled automation layout |
| [n8n/README.md](n8n/README.md) | Dev | n8n orchestration |

## External Orchestration (n8n)

n8n is the external control plane only (scheduling, triggers, ordering, retries).
Business logic remains in Python code inside this repository.

Primary references:

- [`docs/n8n/README.md`](n8n/README.md)
- [`docs/n8n/fulofilo_orchestration_workflow.json`](n8n/fulofilo_orchestration_workflow.json)
- [`docs/USER_GUIDE.md`](USER_GUIDE.md)
- [`docs/AUTOMATIONS_USER_GUIDE.md`](AUTOMATIONS_USER_GUIDE.md)
- [`docs/CODEX_OPERATOR_SETUP_PROMPT.md`](CODEX_OPERATOR_SETUP_PROMPT.md) — Codex: clone, install, open dashboards + guided tour
- [`docs/CODEX_GUIDED_ASSISTANCE_FF.md`](CODEX_GUIDED_ASSISTANCE_FF.md) — Codex: open guided assistance only (port 8502)

## Legacy Notice

Historical CSV/JSON files remain for audit traceability.
They are not active operational write targets.
