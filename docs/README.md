# 🌺 FulôFiló Analytics Pro

Business intelligence dashboard for FulôFiló retail store.
Built for **iMac M3 · macOS · Python 3.13 · local-first, 100% offline**.

Live deployment: https://autogio-fulofilo.streamlit.app/

---

## Quick Start

```bash
cd /Users/giovannini_nuovo/Documents/GitHub/FuloFilo

# 1. Install dependencies
uv sync

# 2. Ingest 2026 sales data (March + April)
.venv/bin/python3 etl/ingest_march_april_2026.py

# 3. Build product catalog
.venv/bin/python3 etl/build_catalog.py

# 4. Launch dashboard
uv run streamlit run app/app.py
# → http://127.0.0.1:8501

# 5. Push changes to GitHub (triggers Streamlit Cloud redeploy)
.venv/bin/python3 etl/sync_and_push.py
```

---

## Project Structure

```
FuloFilo/
├── app/
│   ├── app.py                       # Main dashboard (Visão Geral + Reorder Alerts)
│   ├── db.py                        # DuckDB engine + analytical queries
│   ├── components/
│   │   ├── sidebar.py               # Navigation + period selector (3 buttons)
│   │   └── hud.py                   # Dark HUD theme CSS + Plotly layout
│   ├── pages/
│   │   ├── 01_abc_analysis.py       # ABC Pareto analysis
│   │   ├── 02_margin_matrix.py      # Margin scatter matrix
│   │   ├── 03_inventory.py          # Stock alerts + turnover
│   │   ├── 04_daily_ops.py          # Daily operations view
│   │   ├── 05_categories.py         # Category manager
│   │   └── 06_export_excel.py       # Excel report export
│   └── utils/
│       ├── reorder_engine.py        # Smart reorder alert engine
│       └── inventory_ops.py         # Inventory utility functions
├── data/
│   ├── parquet/                     # Generated Parquet views (gitignored)
│   │   ├── products.parquet         # 3 rows/product × 3 periods (115 rows)
│   │   ├── products_2026.parquet    # Mar+Apr combined
│   │   ├── products_2026_03.parquet # March 2026 only (37 products)
│   │   ├── products_2026_04.parquet # April 2026 only (39 products)
│   │   ├── inventory.parquet        # 532 SKUs, current_stock = 300 each
│   │   ├── daily_sales.parquet      # Transaction log (append-only)
│   │   └── cashflow.parquet         # Cash flow entries
│   ├── raw/                         # Source data (tracked in git)
│   │   ├── dashboard_data_2026.json # Primary 2026 source of truth
│   │   ├── vendas_marco_26.csv      # March 2026 daily sales
│   │   ├── vendas_abril_26.csv      # April 2026 daily sales
│   │   └── product_catalog*.csv     # Product catalog + categories
│   ├── outputs/                     # Auto-generated reports (gitignored)
│   │   └── alertas_reposicao.xlsx   # Reorder alert spreadsheet
│   └── fulofilo.duckdb              # DuckDB database file (gitignored)
├── etl/
│   ├── ingest_march_april_2026.py   # Ingest 2026 sales data
│   ├── build_catalog.py             # Builds products.parquet (all periods)
│   └── sync_and_push.py             # Git add → commit → push (HTTPS)
├── docs/
│   ├── README.md                    # This file
│   ├── DATA_DICTIONARY.md           # Schema reference
│   ├── USER_GUIDE.md                # Operator manual
│   ├── AUDIT_REPORT.md              # Audit log
│   └── SHORTCUTS.md                 # macOS automation setup
└── tests/
    └── test_pipeline.py             # Pipeline tests
```

---

## ETL Pipeline

```
vendas_marco_26.csv  +  vendas_abril_26.csv
dashboard_data_2026.json
        ↓
  ingest_march_april_2026.py
        ↓
  products_2026_03.parquet   (March)
  products_2026_04.parquet   (April)
  products_2026.parquet      (combined)
        ↓
  build_catalog.py
        ↓
  products.parquet            ← 3 rows/product (2026-03, 2026-04, 2026)
  inventory.parquet           ← 532 SKUs, 300 units baseline
        ↓
  DuckDB views (7 views registered at startup)
        ↓
  Streamlit dashboard
        ↓
  reorder_engine.py → alertas_reposicao.xlsx + macOS notification
```

---

## Period Architecture

`products.parquet` stores **3 rows per product** — one per period:

| Period key | Meaning |
|-----------|---------|
| `2026-03` | March 2026 |
| `2026-04` | April 2026 |
| `2026` | March + April combined |

All queries filter by `period` via `db.period_where()` to prevent triple-counting.
The sidebar shows 3 buttons: **Total**, **Março**, **Abril**.

---

## Technology Stack

| Layer | Tool |
|-------|------|
| Runtime | Python 3.13 (Apple Silicon native) |
| Package manager | uv |
| Data storage | DuckDB + Parquet |
| Data processing | Polars (queries) + Pandas (reorder engine) |
| Dashboard | Streamlit |
| Charts | Plotly |
| Excel export | openpyxl |
| Deployment | Streamlit Cloud (auto-redeploy on git push) |

---

## Hardware Target

- **Machine:** Apple iMac M3, 16 GB unified memory
- **DuckDB threads:** 8 (local) / 2 (Streamlit Cloud)
- **DuckDB memory limit:** 8 GB (local) / 512 MB (cloud)

---

## Deployment

Push to GitHub → Streamlit Cloud redeploys automatically in ~60 seconds.

```bash
# Quick push (all tracked files)
.venv/bin/python3 etl/sync_and_push.py

# Custom commit message
.venv/bin/python3 etl/sync_and_push.py --message "add May sales data"

# Validate without pushing
.venv/bin/python3 etl/sync_and_push.py --dry-run
```

Uses HTTPS + macOS Keychain for authentication (no SSH key required).
