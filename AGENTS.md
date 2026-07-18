# AGENTS.md

Operational guide for AI coding agents in **fulofilo-analytics** (FulôFiló AI Retail Operations Terminal).

## What this project is

Local-first retail analytics:

```
Excel master → sync pipeline → Parquet / DuckDB → Streamlit terminal
```

- **Source of truth:** `data/excel/FuloFilo_Master.xlsx` (edit in Excel).
- **Sync:** `bash scripts/sync_excel.sh` → `data/parquet/*.parquet` and `data/fulofilo.duckdb`.
- **Dashboard:** `app/app.py` — read-only for source-owned business data.
- **Orchestration:** n8n schedules only; business logic stays in Python here.

## Folder layout (keep it)

| Path | Purpose |
|------|---------|
| `app/` | Streamlit application code |
| `core/` | Domain logic (analytics, alerts, engines) |
| `etl/` | Ingestion / categorization pipelines |
| `scripts/` | Runnable helpers (`.sh`, `.py`, deploy) |
| `config/` | Non-secret settings (not `configs/`) |
| `data/` | Excel, parquet, DuckDB, raw/processed inputs |
| `assets/` | Brand kit, product images (dashboard logos stay in `app/assets/`) |
| `docs/` | Guides and design notes |
| `docs/prompts/` | AI prompt files |
| `tests/` | Tests only |
| `archive/` | Obsolete files kept for reference |
| `automations/`, `cf-worker/`, `macos/`, `excel/`, `reports/`, `tools/` | Supporting packages — do not invent new top-level folders |

**Root** should stay lean: `README.md`, `AGENTS.md`, `.gitignore`, toolchain files (`pyproject.toml`, `uv.lock`, `Makefile`, `requirements.txt`, `docker-compose*.yml`, `*.code-workspace`), plus Finder launchers `FuloFilo.command` and `FuloFiloOperatorSetup.command`.

Prefer **move** over copy. Prefer **edit** over create. Do not delete unclear files — put them in `archive/`. No secrets in git. No personal machine inventory in this file.

## Host constraints (Apple Silicon)

- **arm64 only.** No CUDA / no `.cuda()` — use MPS with CPU fallback for torch.
- Prefer **Polars (lazy) and DuckDB**; avoid loading full datasets into pandas.
- Do not oversubscribe threads; leave Polars/DuckDB defaults unless profiling says otherwise.
- Keep `.command` launchers executable (`chmod +x`).

## Setup & commands

```bash
uv sync                          # install/refresh (not bare pip)
bash scripts/sync_excel.sh       # after any Excel/data edit
bash scripts/launch_app.sh       # http://127.0.0.1:8501
uv run streamlit run app/app.py
uv run pytest
```

Automation entrypoints (n8n-safe — keep stable):

```bash
make automation-run-daily
make automation-refresh-dashboard-data
make automation-sync-excel-master
make automation-generate-replenishment-alerts
make automation-export-reports
make automation-validate-data-integrity
```

Strict SKU validation: `bash scripts/sync_excel.sh --sku-policy strict`

## Conventions

- Dashboard does **not** write source-owned parquet/duckdb; Excel + sync only.
- Absolute imports from repo root (`from app...`, `from core...`).
- `from __future__ import annotations`, type hints, `pathlib.Path`.
- Workbook backups: `data/excel/backups/FuloFilo_Master_YYYYMMDD_HHMMSS.xlsx`.
- `polars==1.36.1` is pinned — do not bump casually.
- Only commit when the user asks (`feat:` / `fix:` / `data:` / `chore:`).

## Validation

After pipeline/data changes: re-sync, then `uv run pytest`. CI (`.github/workflows/validate.yml`) checks required parquet columns and dashboard JSON keys.
