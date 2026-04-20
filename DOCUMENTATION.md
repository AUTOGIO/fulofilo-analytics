# FulôFiló Analytics Pro
## Technical Documentation and Operator Manual (Apple-Tailored Dashboard Track)

Version: 2.1
Date: April 2026
Target: macOS on Apple Silicon (iMac M3 class), local-first

---

## 1. System Identity

FulôFiló Analytics Pro is a local dashboard and reporting system for store operations and management analytics.

Production track:
- Streamlit dashboard (`app/`)
- DuckDB views over Parquet (`app/db.py`)
- Excel master workbook (`data/excel/FuloFilo_Master.xlsx`) — **canonical source of truth**
- Sync pipeline (`scripts/sync_excel.sh`)

Legacy track (migration fallback only — do not use for normal operations):
- CSV masters under `data/raw/*_master.csv` (Numbers-edited)
- Sync pipeline (`scripts/sync_native_sources.sh`)
- See `scripts/adhoc/` for one-time migration scripts

Non-production side tracks:
- Visual POS CV pipeline (`visual_pos/`, `src/fulofilo_ai/`)
- Cloudflare worker deployment helper (`cf-worker/`) — custom domain redirects to Streamlit Cloud; use `bash scripts/deploy_cloudflare_worker.sh https://…streamlit.app` (not a Tunnel; see header in `cf-worker/worker.js` if you see Error 1033)

These side tracks are buildable but not part of canonical local dashboard operations.

---

## 2. Source of Truth Contract

Canonical source: `data/excel/FuloFilo_Master.xlsx`

Sheets:
- `Catalog` — product master (SKU, name, category, cost, price)
- `Inventory` — stock levels per SKU
- `DailySales` — transaction history
- `Cashflow` — revenue and expense entries
- `CategoryOverrides` — manual category assignments
- `Meta` — workbook metadata

Rules:
- Operators edit the Excel master directly in Microsoft Excel.
- Dashboard pages are read-only for all source-owned datasets.
- Parquet and DuckDB are generated read layers only; never edit them directly.

Canonical sync command:
```bash
bash scripts/sync_excel.sh
```

Sync status artifact:
- `data/excel/source_sync_status.json`

---

## 3. Architecture and Data Flow

```text
Microsoft Excel
data/excel/FuloFilo_Master.xlsx
  (Catalog, Inventory, DailySales, Cashflow, CategoryOverrides, Meta)
        |
        v
scripts/sync_excel.py
  - schema validation (required columns per sheet)
  - SKU uniqueness checks
  - referential integrity (Inventory/Overrides/Sales → Catalog)
  - non-negativity checks (cost, price)
  - sales total reconciliation (Total vs Quantity × Unit_Price, tol=0.02)
  - SKU policy enforcement (balanced/strict)
  - ABC classification (cumulative revenue: A≤80%, B≤95%, C>95%)
  - margin computation (unit_profit, margin_pct)
        |
        v
data/parquet/*.parquet  (products, inventory, daily_sales, cashflow,
                         revenue_report, quantity_report, profit_report)
data/fulofilo.duckdb    (views over parquet)
        |
        v
Streamlit dashboard (read-only over source-owned data)
  app/app.py          — Overview + KPIs
  pages/01_abc_analysis.py    — ABC Pareto
  pages/02_margin_matrix.py   — Margin scatter
  pages/03_inventory.py       — Stock alerts
  pages/04_daily_ops.py       — Sales history
  pages/05_categories.py      — Category manager
  pages/06_export_excel.py    — Excel report builder
        |
        v
excel/build_report.py  (downstream 9-sheet Excel report — read-only artifact)
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

Contract checks run against `data/excel/FuloFilo_Master.xlsx`:
- required columns for all 6 master sheets
- unique SKU constraints (Catalog, Inventory, CategoryOverrides)
- referential integrity: Inventory/CategoryOverrides/DailySales SKU → Catalog SKU
- non-negativity: unit_cost ≥ 0, suggested_price ≥ 0
- sales reconciliation: Total vs Quantity × Unit_Price (tolerance 0.02)

Daily sales SKU policy (`--sku-policy`):
- `balanced` (default):
  - unknown SKU: error
  - blank SKU: warning with KPI-impact count
- `strict`:
  - unknown SKU: error
  - KPI-impact blank SKU rows: error

Strict mode:
```bash
bash scripts/sync_excel.sh --sku-policy strict
```

---

## 6. Operating Procedure

1. Open the Excel master workbook:
```bash
open data/excel/FuloFilo_Master.xlsx
```

2. Edit business data in the relevant sheet (Catalog, Inventory, DailySales, Cashflow, or CategoryOverrides).

3. Run sync:
```bash
bash scripts/sync_excel.sh
```

4. Launch app:
```bash
bash scripts/launch_app.sh
```
Or double-click `FuloFilo.command` in Finder for a self-healing launcher.

5. (Optional) generate Excel report artifact from within the dashboard (page 6 — Exportar Relatório) or via CLI:
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
