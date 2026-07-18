# Sync Workflow — Local to Streamlit Cloud

This document describes how local Excel edits become read models on Streamlit Cloud without adding databases, APIs, or cloud write paths.

## Source of truth

| Asset | Role |
|-------|------|
| `data/excel/FuloFilo_Master.xlsx` | **Only canonical writable source** — edit in Excel on macOS |
| `data/parquet/*.parquet` | Generated read models (reproducible from Excel) |
| `data/fulofilo.duckdb` | Optional bootstrap file; dashboard queries parquet views at runtime |

Streamlit Cloud is **read-only** for business data. It never writes to Excel or runs local sync scripts.

## Local commands

### Sync only (no git)

Regenerate parquets after any Excel edit:

```bash
bash scripts/sync_excel.sh
```

Strict validation (SKU policy + recommended before commits):

```bash
bash scripts/sync_excel.sh --sku-policy strict
uv run pytest tests/test_pipeline.py -q
```

### Validate generated outputs

```bash
bash scripts/validate_generated_data.sh
```

Checks: Excel master exists, parquet directory non-empty, all 7 canonical parquets readable, no zero-byte files.

### Full publish (sync + validate + commit + push)

```bash
bash scripts/sync_and_push.sh
```

### Dry-run (safe preview)

Runs sync and validation, shows what would be committed — **no commit, no push**:

```bash
bash scripts/sync_and_push.sh --dry-run
```

Optional strict gate (adds pytest):

```bash
bash scripts/sync_and_push.sh --with-tests
```

## Deploy flow

```text
Excel master (local edit)
  → scripts/sync_excel.sh
  → data/parquet/*.parquet (+ product_catalog.csv)
  → local Streamlit dashboard (http://127.0.0.1:8501)
  → scripts/sync_and_push.sh
  → git commit + push
  → GitHub
  → Streamlit Cloud redeploy (~60s)
  → https://autogio-fulofilo.streamlit.app/
```

From the dashboard sidebar (local only): **Sync & Push** runs `scripts/sync_and_push.sh` and shows an expandable log.

## What Streamlit Cloud reads

- Versioned files under `data/parquet/` (committed to git)
- `data/excel/FuloFilo_Master.xlsx` when changed and pushed
- Parquet-backed DuckDB views created in memory at app startup (`app/db.py`)

Cloud does **not** run `scripts/sync_excel.sh` or `scripts/sync_and_push.sh`.

## What cloud must never do

- Write or mutate `FuloFilo_Master.xlsx`
- Run Loyverse/Rede automations or subprocess sync scripts
- Add PostgreSQL, Supabase, queues, or external ETL infrastructure

The sidebar gates local-only actions with `_is_streamlit_cloud()`.

## Branch note

`sync_and_push.sh` pushes to your **current git branch** and warns if it is not `main`. Streamlit Cloud typically deploys from `main` — push to `main` when you want the public app to update.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `venv missing` | `cd` to repo root, run `uv sync` |
| Sync fails | Check `data/excel/source_sync_status.json` for errors; fix Excel data |
| Validation fails on zero-byte parquet | Re-run `bash scripts/sync_excel.sh` |
| `git push failed` | Ensure HTTPS remote and credentials (`gh auth login` or macOS Keychain) |
| Cloud did not update | Confirm you pushed to `main`; wait ~60s; check GitHub Actions |
| Detached HEAD / merge in progress | Resolve git state before running sync_and_push |
| CI validate.yml fails | Review `.github/workflows/validate.yml` column expectations vs current parquet schema |

## Related

- Root quick start: [README.md](../README.md)
- Re-sync rules: [docs/README.md](README.md)
- Strict integrity gate: `make automation-validate-data-integrity`
- Legacy git-only push (deprecated): `etl/sync_and_push.py` → use `scripts/sync_and_push.sh`
