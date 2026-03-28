# FulôFiló Analytics Pro

**Local-first business intelligence dashboard for FulôFiló.**
Built on macOS Apple Silicon (iMac M3) — no cloud APIs required.

---

## What this project does

FulôFiló Analytics Pro is a Streamlit dashboard that transforms daily sales, inventory, and product catalog data into actionable business intelligence. It covers:

- **Product portfolio classification** — automatic Star / Cash Cow / Hidden Gem / Dog quadrant assignment using dynamic median thresholds
- **Action recommendations** — per-product recommended action generated from classification
- **Operational alerts** — real-time stock risk detection (low stock on Stars, overstock on Dogs)
- **Daily sales management** — register, view, filter, and delete sales; auto-sync to Excel
- **Inventory control** — stock adjustment with bidirectional sync to Excel workbook
- **ABC analysis** — revenue-ranked product classification (A/B/C tiers)
- **Margin matrix** — volume × margin scatter plot with quadrant annotations
- **Category manager** — view, filter, and reassign product categories
- **Weekly decision reports** — JSON + Markdown output generated on demand
- **Excel bidirectional sync** — dashboard mutations write back to `FuloFilo_Report.xlsx`
- **Auto-refresh** — dashboard detects parquet file changes via mtime fingerprinting; no manual reload needed

---

## Architecture

```
app/                         ← Streamlit application
  app.py                     ← Main dashboard (Visão Geral)
  pages/
    01_abc_analysis.py       ← ABC analysis
    02_margin_matrix.py      ← Margin matrix + intelligence layer
    03_inventory.py          ← Inventory management + stock turnover
    04_daily_ops.py          ← Daily sales: register, filter, delete, sync
    05_categories.py         ← Category manager
    06_export_excel.py       ← Excel export
  components/
    sidebar.py               ← Shared sidebar, logo, navigation
    hud.py                   ← HUD dark-theme CSS + Plotly layout
  db.py                      ← DuckDB connection + all query functions
  utils/
    inventory_ops.py         ← Stock mutations: decrement, adjust, sync
    sales_ops.py             ← CSV → Excel daily ops sync

core/                        ← Business intelligence layer (Phase 1/2)
  classification.py          ← Dynamic median-threshold quadrant classifier
  recommendations.py         ← Centralized action mapping engine
  reporting.py               ← Weekly report generator (JSON + Markdown)
  alerts.py                  ← Operational alerts with graceful degradation
  analytics.py               ← Category-level aggregation

data/
  parquet/                   ← Live data (tracked in git)
    products.parquet
    inventory.parquet
    daily_sales.parquet
    cashflow.parquet
  raw/
    daily_sales_TEMPLATE.csv ← Source of truth for daily sales
    product_catalog_categorized.csv
  outputs/                   ← Generated reports (gitignored)
    weekly_report.json
    weekly_report.md

excel/
  build_report.py            ← Builds FuloFilo_Report_YYYY-MM-DD.xlsx
  FuloFilo_Report_TEMPLATE.xlsx

etl/
  build_catalog.py           ← Builds products.parquet from catalog CSV
```

---

## Dashboard pages

| Page | Description |
|---|---|
| 🏠 Visão Geral | KPI cards: revenue, transactions, avg ticket, total profit |
| 📊 Análise ABC | ABC product ranking by cumulative revenue share |
| 💹 Matriz de Margem | Volume × Margin scatter + **intelligence layer** |
| 📦 Estoque | Inventory table, stock turnover (giro), stock adjustment |
| ⚡ Operações Diárias | Register sales, date-range filter, charts, delete a sale |
| 🏷️ Categorias | Product category management and reassignment |
| 📤 Exportar Excel | Rebuild and download the Excel report |

---

## Intelligence layer (`core/`)

Added to the Margin Matrix page. Runs automatically on every dashboard load.

### Classification engine (`core/classification.py`)

- Thresholds: `vol_threshold = median(qty_sold)`, `margin_threshold = median(margin_pct)`
- Labels: **Star** (high vol + high margin), **Cash Cow** (high vol + low margin), **Hidden Gem** (low vol + high margin), **Dog** (low vol + low margin)
- Deterministic. Handles nulls and empty datasets safely.

### Recommendation engine (`core/recommendations.py`)

| Classification | Recommended action |
|---|---|
| Star | Scale stock + ads + test price increase |
| Cash Cow | Optimize cost + bundle |
| Hidden Gem | Increase visibility + test campaigns |
| Dog | Fix or discontinue |

### Weekly report (`core/reporting.py`)

Generates `data/outputs/weekly_report.json` and `weekly_report.md`.

Sections: Stars, Cash Cows, Hidden Gems, Dogs, and **Pareto revenue concentration** (products that represent 80% of total revenue).

Trigger: "📥 Gerar Relatório" button in the Margin Matrix page.

### Alerts engine (`core/alerts.py`)

| Rule | Status | Trigger |
|---|---|---|
| `star_low_stock` | ✅ Active | Star product with `current_stock ≤ min_stock` → high severity |
| `dog_high_stock` | ✅ Active | Dog product with `current_stock > reorder_qty` → medium severity |
| `hidden_gem_rising_volume` | ⚠️ Skipped | Requires time-series history not available in current schema |

### Category analytics (`core/analytics.py`)

Aggregates per category: avg margin, total revenue, total qty sold, product count, Star count, Dog count.

---

## Data flow

```
daily_sales_TEMPLATE.csv
        │
        ▼
  _rebuild_parquet()          ← triggered on every sale or delete
        │
        ├── daily_sales.parquet  (DuckDB view)
        │
        └── sync_csv_to_excel_daily_ops()  ── FuloFilo_Report.xlsx [Daily Ops]

inventory.parquet
        │
        ├── DuckDB view  ── dashboard reads
        └── sync_to_excel()  ── FuloFilo_Report.xlsx [Inventory]

products.parquet
        └── DuckDB view  ── ABC, Margin Matrix, intelligence layer
```

---

## Auto-refresh mechanism

All cached load functions use a `data_version: str` parameter instead of a fixed TTL:

```python
@st.cache_data
def load(data_version: str):
    ...

load(get_data_mtime())   # re-runs only when a parquet file changes
```

`get_data_mtime()` returns the max mtime across all `data/parquet/*.parquet` files as a string. A mutation (sale, stock adjust) updates a parquet → mtime changes → cache miss → dashboard refreshes automatically.

---

## Excel bidirectional sync

Every sale registration and stock adjustment writes back to `FuloFilo_Report_YYYY-MM-DD.xlsx`:

- `inventory_ops.sync_to_excel()` → updates **Inventory** sheet by SKU
- `sales_ops.sync_csv_to_excel_daily_ops()` → rewrites **Daily Ops** sheet from full CSV aggregated by day

---

## Setup

```bash
cd /Users/eduardogiovannini/dev/products/FuloFilo

# Install dependencies
pip install -r requirements.txt

# Build product catalog (first run or after catalog changes)
python3 etl/build_catalog.py

# Launch dashboard
streamlit run app/app.py --server.port 8501
```

The dashboard is also exposed via Cloudflare Tunnel at `dashboard.giovannini.us`.

---

## Run with launchctl (macOS service)

Streamlit and the Cloudflare tunnel are managed as `launchctl` services for always-on operation on the iMac M3.

---

## Validate intelligence layer

```bash
cd /Users/eduardogiovannini/dev/products/FuloFilo

python3 -c "
import polars as pl, sys; sys.path.insert(0, '.')
from core.classification import classify_dataframe
from core.recommendations import enrich_with_recommendations
from core.reporting import generate_weekly_report
from core.alerts import generate_alerts

products  = pl.read_parquet('data/parquet/products.parquet').to_pandas()
inventory = pl.read_parquet('data/parquet/inventory.parquet').to_pandas()

enriched = enrich_with_recommendations(classify_dataframe(products))
print(enriched[['full_name','classification','recommended_action']].to_string())
print(generate_alerts(enriched, inventory)['summary'])
generate_weekly_report(enriched)   # writes data/outputs/weekly_report.json
"
```

---

## Current validated results (42 products, 2026-03-28)

| Metric | Value |
|---|---|
| Stars | 21 |
| Hidden Gems | 14 |
| Dogs | 7 |
| Cash Cows | 0 (all high-vol products have above-median margin) |
| Active alerts | 5 (4 × star_low_stock, 1 × dog_high_stock) |
| Revenue concentration | 28 products (66.7%) → 81.4% of revenue |
| Vol threshold | 78.5 units |
| Margin threshold | 58.0% |

---

## Key files

| File | Purpose |
|---|---|
| `app/db.py` | DuckDB connection, all query functions, `get_data_mtime()` |
| `app/utils/inventory_ops.py` | Stock mutations + Excel sync |
| `app/utils/sales_ops.py` | CSV→Excel Daily Ops sync |
| `core/classification.py` | Product classifier |
| `core/recommendations.py` | Action mapping |
| `core/reporting.py` | Weekly report generator |
| `core/alerts.py` | Operational alerts |
| `core/analytics.py` | Category aggregation |
| `excel/build_report.py` | Excel workbook builder |
| `fill_csv_history.py` | Seed script: generates 60 days of historical sales data |

---

## Tech stack

- **Python 3.10** — macOS Apple Silicon (M3)
- **Streamlit** — dashboard UI
- **DuckDB** — in-process analytics over Parquet files
- **Polars** — fast DataFrame operations in ETL/queries
- **Pandas** — UI layer and core module operations
- **Plotly** — interactive charts (HUD dark theme)
- **openpyxl** — Excel read/write with MergedCell safety
- **Cloudflare Tunnel** — exposes local dashboard to `dashboard.giovannini.us`

---

*FulôFiló Analytics Pro — local-first, Apple Silicon, zero cloud dependencies.*
