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

**Row 1 headers (exact names, as implemented in `scripts/sync_excel.py`):**

| Sheet | Columns |
|-------|---------|
| Catalog | `sku`, `full_name`, `category`, `unit_cost`, `suggested_price`, `min_stock`, `reorder_qty` |
| Inventory | `sku`, `product`, `category`, `current_stock`, `min_stock`, `reorder_qty`, `supplier`, `lead_time_days`, `notes` |
| DailySales | `Date`, `sku`, `Product`, `Quantity`, `Unit_Price`, `Total`, `Payment_Method`, `Source` |
| Cashflow | `Date`, `Type`, `Category`, `Description`, `Amount`, `Payment_Method` |
| CategoryOverrides | `sku`, `category`, `subcategory`, `confidence` |
| Meta | `key`, `value` |

First-time workbook: `uv run python scripts/bootstrap_excel_master.py`

Rules:
- Operators edit the Excel master directly in Microsoft Excel.
- Dashboard pages are read-only for all source-owned datasets.
- Parquet and DuckDB are generated read layers only; never edit them directly.
- Generated report workbooks (`excel/FuloFilo_Report_*.xlsx`) are **read-only artifacts** — they must never be used as operational sync targets.
- All runtime stock mutations (inventory adjustments, daily sales sync) write back exclusively to `data/excel/FuloFilo_Master.xlsx` via `app/utils/inventory_ops.py` and `app/utils/sales_ops.py`.
- Every stock write (decrement or manual adjustment) is appended to `data/logs/stock_audit.csv` as an immutable audit trail.

Canonical sync command:
```bash
bash scripts/sync_excel.sh
```

Sync status artifact:
- `data/excel/source_sync_status.json`

---

## 3. Architecture and Data Flow

```text
data/excel/FuloFilo_Master.xlsx  ← SINGLE CANONICAL WRITE TARGET
  (Catalog, Inventory, DailySales, Cashflow, CategoryOverrides, Meta, Daily Ops)
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
Streamlit dashboard
  app/app.py          — Overview + KPIs
  pages/01_abc_analysis.py    — ABC Pareto
  pages/02_margin_matrix.py   — Margin scatter
  pages/03_inventory.py       — Stock alerts + adjustments
  pages/04_daily_ops.py       — Sales entry
  pages/05_categories.py      — Category manager
  pages/06_export_excel.py    — Excel report builder
        |
        | stock adjustments & daily sales write-back (via inventory_ops / sales_ops)
        v
data/excel/FuloFilo_Master.xlsx  ← write-back to Inventory + Daily Ops sheets
data/logs/stock_audit.csv        ← append-only audit trail (every stock mutation)
        |
        v
excel/build_report.py → excel/FuloFilo_Report_*.xlsx  (READ-ONLY artifact — never mutated after generation)
```

**Write-back contract:**
- `app/utils/inventory_ops.py::sync_to_excel()` → writes only to `data/excel/FuloFilo_Master.xlsx` (Inventory sheet, cols D–F)
- `app/utils/sales_ops.py::sync_csv_to_excel_daily_ops()` → writes only to `data/excel/FuloFilo_Master.xlsx` (Daily Ops sheet)
- Generated report workbooks under `excel/` receive **zero runtime writes** after build

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
