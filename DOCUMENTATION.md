# FulôFiló Analytics Pro
## Technical Documentation and Operator Manual (Apple-Tailored Dashboard Track)

Version: 2.0  
Date: March 2026  
Target: macOS 26.x on Apple Silicon (iMac M3 class), local-first

---

## 1. System Identity

FulôFiló Analytics Pro is a local dashboard and reporting system for store operations and management analytics.

Production track:
- Streamlit dashboard (`app/`)
- DuckDB views over Parquet (`app/db.py`)
- Numbers-edited CSV masters (`data/raw/*_master.csv`)
- Sync pipeline (`scripts/sync_native_sources.sh`)

Non-production side tracks:
- Visual POS CV pipeline (`visual_pos/`, `src/fulofilo_ai/`)
- Cloudflare worker deployment helper (`cf-worker/`) — custom domain redirects to Streamlit Cloud; use `bash scripts/deploy_cloudflare_worker.sh https://…streamlit.app` (not a Tunnel; see header in `cf-worker/worker.js` if you see Error 1033)

These side tracks are buildable but not part of canonical local dashboard operations.

---

## 2. Source of Truth Contract

Canonical source files under `data/raw/`:
- `catalog_master.csv`
- `inventory_master.csv`
- `daily_sales_master.csv`
- `cashflow_master.csv`
- `category_overrides.csv`

Rules:
- Operators edit masters in Numbers.
- Dashboard pages do not directly mutate source-owned datasets.
- Parquet and DuckDB are generated read layers only.

Canonical sync command:
```bash
bash scripts/sync_native_sources.sh
```

Sync status artifact:
- `data/raw/source_sync_status.json`

---

## 3. Architecture and Data Flow

```text
Numbers (CSV masters under data/raw/)
        |
        v
scripts/sync_native_sources.py
  - schema checks
  - key integrity checks
  - SKU validation policy
  - derived models build
        |
        v
data/parquet/*.parquet
data/fulofilo.duckdb (views)
        |
        v
Streamlit dashboard (read-only over source-owned data)
        |
        v
Excel export artifact (downstream reporting only)
```

---

## 4. Launch Paths (Local)

Terminal launcher:
```bash
bash scripts/launch_app.sh
```

Finder launcher (canonical GUI path):
- Double-click `FuloFilo.command`

Both launchers validate `.venv` health using:
- `.venv/bin/python3`
- `.venv/bin/streamlit`

If venv is missing/corrupt, `FuloFilo.command` heals via `uv sync`.

---

## 5. Validation and SKU Policy

Contract checks:
- required columns for all 5 master CSVs
- unique SKU constraints where applicable
- referential integrity: inventory/overrides/sales SKU against catalog SKU

Daily sales SKU policy (`--sku-policy`):
- `balanced` (default):
  - unknown SKU: error
  - blank SKU: warning with KPI-impact count
- `strict`:
  - unknown SKU: error
  - KPI-impact blank SKU rows: error

Strict mode:
```bash
bash scripts/sync_native_sources.sh --sku-policy strict
```

---

## 6. Operating Procedure

1. Open source files in Numbers:
```bash
bash scripts/open_native_sources.sh
```

2. Edit business data in masters.

3. Run sync:
```bash
bash scripts/sync_native_sources.sh
```

4. Launch app:
```bash
bash scripts/launch_app.sh
```

5. (Optional) generate Excel artifact:
```bash
python3 excel/build_report.py
```

---

## 7. Testing

Run regression suite:
```bash
.venv/bin/python3 -m pytest -q tests/test_pipeline.py
```

The suite covers:
- source contract integrity
- sync invariants
- derived Parquet existence/columns
- sync status output
- Excel build path

---

## 8. Hardware Profile Defaults

- Machine class: Apple Silicon iMac M3, 8 CPU cores, 16 GB RAM
- DuckDB local tuning in `app/db.py`:
  - `threads = 8`
  - `memory_limit = '8GB'`
  - local temp dir `/tmp/duckdb_fulofilo`

These defaults are bounded for stability in local-only operation.
