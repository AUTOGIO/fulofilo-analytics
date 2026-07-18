# FulôFiló — Update Guide
> Last updated: 2026-05-11  
> Dashboard: https://autogio-fulofilo.streamlit.app/  
> Repo: https://github.com/AUTOGIO/fulofilo-analytics

---

## Architecture at a Glance

```
POS Export (CSV)
      │
      ▼
data/incoming/          ← drop CSV here
      │
      ▼
scripts/sync_excel.sh   ← single command does everything below
      │
      ├─► FuloFilo_Master.xlsx   (source of truth — never edit directly)
      ├─► data/parquet/*.parquet  (read models)
      └─► data/fulofilo.duckdb   (query layer)
                │
                ▼
         git push origin main
                │
                ▼
     autogio-fulofilo.streamlit.app  (~90 sec)
```

**Golden rule:** `FuloFilo_Master.xlsx` is the only file you ever write to.  
Everything else is generated — never edit parquets, duckdb, or Report files directly.

---

## 1. Update Sales

### Source file
```
data/incoming/item-sales-summary-YYYY-MM-DD-YYYY-MM-DD.csv
```
Export this file from your POS system. The filename **must** follow that exact pattern.

### Required CSV columns (case-sensitive)
| Column | Example |
|---|---|
| `Item` | Regional adulto |
| `SKU` | 10014 |
| `Itens vendidos` | 655.000 |
| `Vendas líquidas` | 36025.00 |
| `Custo das mercadorias` | 18030.00 |

### Steps
```bash
# 1. Drop the CSV
cp ~/Downloads/item-sales-summary-2026-05-01-2026-05-31.csv \
   /Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/incoming/

# 2. Run ingest + sync (one command)
cd /Users/giovannini_nuovo/Documents/GitHub/FuloFilo
bash scripts/sync_excel.sh

# 3. Verify
cat data/excel/source_sync_status.json | python3 -m json.tool | grep -E "healthy|rows|readiness"
# Expected: healthy_production_data: true, readiness_state: ready

# 4. Push → dashboard live in ~90s
git add data/parquet/ data/fulofilo.duckdb \
        data/excel/FuloFilo_Master.xlsx \
        data/excel/source_sync_status.json
git commit -m "sync: sales YYYY-MM-DD → YYYY-MM-DD"
git push origin main
```

### Alternative: double-click (no terminal)
```
double-click → scripts/ingest_sales.command
```
Drops CSV in `data/incoming/` automatically after processing.

---

## 2. Update Inventory

Inventory is stored in the `Inventory` sheet of `FuloFilo_Master.xlsx`.

### File
```
data/excel/FuloFilo_Master.xlsx  →  sheet: Inventory
```

### Required columns
| Column | Type | Rule |
|---|---|---|
| `sku` | string | Must exist in Catalog |
| `product` | string | Product name |
| `category` | string | Category |
| `current_stock` | int | Current units on hand |
| `min_stock` | int | Alert threshold |
| `reorder_qty` | int | Units to order |
| `supplier` | string | Optional |
| `lead_time_days` | int | Optional |

### Steps
```bash
# 1. Backup first
cp data/excel/FuloFilo_Master.xlsx \
   "data/excel/backups/FuloFilo_Master_$(date +%Y%m%d_%H%M%S).xlsx"

# 2. Open and edit the Inventory sheet in Excel
open data/excel/FuloFilo_Master.xlsx
# → Edit column: current_stock for each SKU
# → Save and close Excel before running sync

# 3. Sync
cd /Users/giovannini_nuovo/Documents/GitHub/FuloFilo
bash scripts/sync_excel.sh

# 4. Push
git add data/parquet/ data/fulofilo.duckdb \
        data/excel/FuloFilo_Master.xlsx \
        data/excel/source_sync_status.json
git commit -m "inventory: update stock counts YYYY-MM-DD"
git push origin main
```

---

## 3. Update Catalog / Metrics (prices, costs, new SKUs)

The `Catalog` sheet drives all margin and ABC metrics.

### File
```
data/excel/FuloFilo_Master.xlsx  →  sheet: Catalog
```

### Required columns
| Column | Type | Rule |
|---|---|---|
| `sku` | string | Unique |
| `full_name` | string | Product name |
| `category` | string | e.g. Roupas, Bolsas, Outros |
| `unit_cost` | float | Cost per unit (R$) |
| `suggested_price` | float | Must be > unit_cost |
| `min_stock` | int | Reorder alert level |
| `reorder_qty` | int | Units to reorder |

### Steps
```bash
# 1. Backup
cp data/excel/FuloFilo_Master.xlsx \
   "data/excel/backups/FuloFilo_Master_$(date +%Y%m%d_%H%M%S).xlsx"

# 2. Open and edit the Catalog sheet
open data/excel/FuloFilo_Master.xlsx
# → Edit unit_cost and/or suggested_price
# → Add new SKUs at the bottom (also add to Inventory sheet)
# → Save and close before syncing

# 3. Sync — rebuilds margins, ABC, cum_pct
cd /Users/giovannini_nuovo/Documents/GitHub/FuloFilo
bash scripts/sync_excel.sh

# 4. Verify metrics
cat data/excel/source_sync_status.json | python3 -m json.tool | grep catalog_real_rows
# Must be > 0 and match your SKU count

# 5. Push
git add data/parquet/ data/fulofilo.duckdb \
        data/excel/FuloFilo_Master.xlsx \
        data/excel/source_sync_status.json
git commit -m "catalog: update costs/prices YYYY-MM-DD"
git push origin main
```

---

## 4. Regenerate the Excel Report

The Report is a formatted 9-sheet workbook built from parquets.  
Rebuild it whenever you want a fresh snapshot to share externally.

### Output file
```
excel/FuloFilo_Report_YYYY-MM-DD.xlsx   ← generated, never edit
```

### Steps
```bash
cd /Users/giovannini_nuovo/Documents/GitHub/FuloFilo

# Run after sync_excel.sh (parquets must be current)
.venv/bin/python3 excel/build_report.py

# File is saved to excel/FuloFilo_Report_YYYY-MM-DD.xlsx
# Open to review:
open excel/FuloFilo_Report_$(date +%Y-%m-%d).xlsx
```

### Report sheets
| Sheet | Contents |
|---|---|
| Dashboard | KPI summary — revenue, margin, top products |
| ABC Analysis | Full Pareto ranking, all 71 SKUs |
| Margin Matrix | Pricing panel — cost vs price vs margin |
| Inventory | Stock levels, reorder status, days runway |
| Daily Ops | Day-by-day sales and cashflow |
| Cashflow | Monthly income / expense / runway |
| Products Catalog | Full catalog with sales data |
| Product Categories | Category rollup |
| Pivot Cat×Month | Revenue by category × month |

---

## 5. Update the Web Dashboard (Cloudflare/Streamlit)

The live dashboard reads parquets directly from GitHub.  
**There is no manual deploy step** — a `git push` is enough.

### URL
```
https://autogio-fulofilo.streamlit.app/
```

### Steps
```bash
cd /Users/giovannini_nuovo/Documents/GitHub/FuloFilo

# After any sync_excel.sh run:
git add data/parquet/ data/fulofilo.duckdb \
        data/excel/FuloFilo_Master.xlsx \
        data/excel/source_sync_status.json

git commit -m "sync: <brief description>"
git push origin main

# Dashboard refreshes automatically within ~90 seconds
```

### What the dashboard reads
| File | Used for |
|---|---|
| `data/parquet/products.parquet` | ABC class, revenue, margin, qty sold |
| `data/parquet/daily_sales.parquet` | Daily revenue chart |
| `data/parquet/inventory.parquet` | Stock levels, reorder alerts |
| `data/parquet/cashflow.parquet` | Cashflow chart |
| `data/parquet/revenue_report.parquet` | Top products table |
| `data/parquet/profit_report.parquet` | Profit ranking |
| `data/fulofilo.duckdb` | Query layer (analytics page) |

---

## Full Update Sequence (all at once)

Use this when you have a new sales CSV and want everything refreshed end-to-end:

```bash
cd /Users/giovannini_nuovo/Documents/GitHub/FuloFilo

# Step 1 — Drop sales CSV
cp ~/Downloads/item-sales-summary-YYYY-MM-DD-YYYY-MM-DD.csv data/incoming/

# Step 2 — Sync everything (ingest + parquets + master xlsx)
bash scripts/sync_excel.sh

# Step 3 — Regenerate Excel report
.venv/bin/python3 excel/build_report.py

# Step 4 — Verify
cat data/excel/source_sync_status.json | python3 -m json.tool | grep -E "healthy|rows"

# Step 5 — Push (dashboard goes live in ~90s)
git add data/parquet/ data/fulofilo.duckdb \
        data/excel/FuloFilo_Master.xlsx \
        data/excel/source_sync_status.json
git commit -m "sync: sales YYYY-MM-DD → YYYY-MM-DD"
git push origin main
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `healthy_production_data: false` | Placeholder SKU in Catalog | Remove `00001 / Produto Exemplo` from Catalog sheet |
| Dashboard shows old data | Parquets not pushed | `git push origin main` |
| `readiness_state: bootstrap` | Catalog empty or all placeholders | Add real SKUs to Catalog |
| KPIs show 3× expected | Missing period filter | Re-run `sync_excel.sh` — do not query parquets directly |
| Ingest rejects CSV | Wrong filename or missing columns | Check filename pattern and required columns (Section 1) |
| `git push` rejected | Local behind remote | `git pull --rebase origin main` then push again |
| openpyxl broken in venv | Package corruption | `.venv/bin/python3 -m pip install --upgrade openpyxl --force-reinstall` |

---

## Key Paths Reference

```
Project root:   /Users/giovannini_nuovo/Documents/GitHub/FuloFilo/
Master Excel:   data/excel/FuloFilo_Master.xlsx
Backups:        data/excel/backups/
Incoming CSV:   data/incoming/                     ← drop POS exports here
Parquets:       data/parquet/                      ← generated, do not edit
DuckDB:         data/fulofilo.duckdb               ← generated, do not edit
Raw archive:    data/raw/                          ← processed CSVs archived here
Report output:  excel/FuloFilo_Report_YYYY-MM-DD.xlsx
Sync script:    scripts/sync_excel.sh
Ingest script:  scripts/ingest_sales.command       ← double-click friendly
Build report:   excel/build_report.py
Sync status:    data/excel/source_sync_status.json
```
