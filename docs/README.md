# 🌺 FulôFiló Analytics Pro

Business intelligence dashboard for FulôFiló retail store.
Built for **iMac M3 · macOS 26.4 · Python 3.13 · local-first, 100% offline**.

## Quick Start

```bash
cd /Users/eduardogiovannini/dev/products/FuloFilo

# 1. Install dependencies
uv sync

# 2. Build product catalog
.venv/bin/python3 etl/build_catalog.py

# 3. Ingest Eleve Vendas export
.venv/bin/python3 etl/ingest_eleve.py

# 4. Categorize products
.venv/bin/python3 etl/categorize_products.py

# 5. Launch dashboard
./scripts/launch_app.sh
# → http://127.0.0.1:8501

# 6. Generate Excel report
.venv/bin/python3 excel/build_report.py
```

## Project Structure

```
FuloFilo/
├── app/
│   ├── app.py                  # Main Streamlit shell
│   ├── db.py                   # DuckDB engine + queries
│   └── pages/
│       ├── 01_abc_analysis.py  # ABC Pareto analysis
│       ├── 02_margin_matrix.py # Margin scatter matrix
│       ├── 03_inventory.py     # Stock alerts + reorder
│       ├── 04_daily_ops.py     # Daily operations view
│       ├── 05_categories.py    # Category manager
│       └── 06_export_excel.py  # Excel report export
├── data/
│   ├── parquet/                # Generated data (gitignored)
│   ├── raw/                    # Source data (tracked)
│   └── fulofilo.duckdb         # Database (gitignored)
├── etl/
│   ├── build_catalog.py        # Builds products.parquet
│   ├── ingest_eleve.py         # Processes Eleve Vendas JSON
│   └── categorize_products.py  # Rule-based categorization
├── excel/
│   └── build_report.py         # 9-sheet Excel workbook builder
├── scripts/
│   ├── launch_app.sh           # Streamlit launcher (M3 optimized)
│   └── refresh_data.sh         # Full pipeline refresh
├── tests/
│   └── test_pipeline.py        # 6 pytest tests
├── docs/
│   ├── README.md               # This file
│   ├── SHORTCUTS.md            # macOS automation setup
│   └── DATA_DICTIONARY.md      # Schema reference
```

## ETL Pipeline

```
dashboard_data.json (Eleve Vendas)
        ↓
  ingest_eleve.py
        ↓
  revenue_report.parquet
  quantity_report.parquet      build_catalog.py
  profit_report.parquet    ←── product_catalog.csv
  daily_sales.parquet              ↓
  cashflow.parquet          products.parquet
  inventory.parquet                ↓
        ↓                  categorize_products.py
  DuckDB views                     ↓
        ↓            product_catalog_categorized.csv
  Streamlit + Excel
```

## Running Tests

```bash
.venv/bin/python3 -m pytest tests/test_pipeline.py -v
# Expected: 6 passed
```

## Technology Stack

| Layer | Tool |
|-------|------|
| Runtime | Python 3.13 (Apple Silicon native) |
| Package manager | uv |
| Data storage | DuckDB + Parquet |
| Data processing | Polars |
| Dashboard | Streamlit |
| Charts | Plotly |
| Excel export | openpyxl |

## Hardware Target

- **Machine:** Apple iMac M3, 16 GB unified memory
- **OS:** macOS 26.4 (25E241)
- **DuckDB threads:** 8 (M3 performance cores)
- **DuckDB memory limit:** 12 GB
