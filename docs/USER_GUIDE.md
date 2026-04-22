# DELIVERABLE 2 — USER GUIDE

**FulôFiló Analytics Pro** — Operator manual (Apple Silicon, macOS, local-first)

---

## Before you start: two ways to feed the system

| You have… | Do this |
|-----------|---------|
| **Eleve JSON** in `data/raw/dashboard_data.json` (optional drop into `~/Documents/FuloFilo_Inbox/`) | Run **`./scripts/refresh_data.sh`** after edits/exports |
| **Excel master** at `data/excel/FuloFilo_Master.xlsx` | Run **`bash scripts/sync_excel.sh`** after saving the workbook |

**Alternate path:** If you use Eleve JSON and the embedded catalog instead of the master workbook, use **`./scripts/refresh_data.sh`** and keep `data/raw/dashboard_data.json` current. Avoid running both syncs blindly in the same session unless you know how they interact.

---

## 1. Introduction

**What it is:** A local dashboard that shows sales KPIs, ABC classification, margin positioning, inventory health, daily operations, and categories — plus one-click Excel reports.

**Why it matters:** You decide what to stock, promote, or discontinue using the same numbers executives see.

**How it works:** Data becomes Parquet files → DuckDB → Streamlit pages.

**How to use:** Edit sources → refresh → open the app → act on insights → export if needed.

**What can fail:** Old data (forgot refresh), missing files, port already in use.

**How to fix it:** See §8 and §9.

---

## 2. Quick Start

**Objective:** See the dashboard in under five minutes (after repo + data exist).

| Step | Action | Expected outcome | Common mistake |
|------|--------|------------------|----------------|
| 1 | Open Terminal; `cd` to project folder | Shell in repo root | Wrong folder → `uv` creates venv elsewhere |
| 2 | `uv sync` | `.venv` ready | Skipping → launch scripts error |
| 3 | `./scripts/refresh_data.sh` | Parquet updated | No JSON → ingest fails |
| 4 | `./scripts/launch_app.sh` or double-click **`FuloFilo.command`** | Browser at `http://127.0.0.1:8501` | Firewall blocking localhost (rare) |

**Validation:** Home page shows KPI cards (values depend on your data).

**Screenshot:** [SCREENSHOT: Dashboard Home]

---

## 3. Daily Workflow

**Objective:** Keep numbers trustworthy every selling day.

| Step | Who | Action |
|------|-----|--------|
| Morning | Operator | Open sources: target Excel **`FuloFilo_Master.xlsx`**, or confirm **`dashboard_data.json`** / manual CSVs |
| During day | Operator | Record sales (POS export or **Operações Diárias** form) |
| After changes | Operator | Run **`bash scripts/sync_excel.sh`** (Excel) **or** **`./scripts/refresh_data.sh`** (Eleve JSON path) |
| Review | Manager | Open dashboard — ABC, estoque, margem |
| Optional | Analyst | **Exportar Excel** for sharing |

**Expected outcome:** Dashboard matches your latest source data.

**Common mistake:** Editing Parquet manually — always regenerate from sources.

---

## 4. Dashboard Pages Explained

Navigation order matches the sidebar (see `app/components/sidebar.py`).

### 4.1 Visão Geral (`app.py`)

**What:** Top-level KPIs: receita, unidades, lucro bruto, margem %, ticket médio; top 15 products by revenue; revenue by category pie; ABC summary table.

**Why:** Single glance health of the business.

**How to use:** Open first after every sync.

**What can fail:** Empty charts if no sales in `products`.

**Fix:** Run ETL; confirm `products.parquet` has rows.

[SCREENSHOT: Dashboard Home]

### 4.2 Análise ABC (`01_abc_analysis.py`)

**What:** Pareto view — class **A** ≈ first ~80% cumulative revenue, **B** next ~15%, **C** remainder (see [DATA_DICTIONARY.md](DATA_DICTIONARY.md)); filters, treemap, decision hints.

**Why:** Focus time on SKUs that drive results.

**How to use:** Filter categories; read badges/decision tags.

**Fail / fix:** “Execute `etl/build_catalog.py`” → run full refresh.

### 4.3 Matriz de Margem (`02_margin_matrix.py`)

**What:** Scatter: volume vs margin %; quadrants **Stars**, **Cash Cows**, **Hidden Gems**, **Dogs**.

**Why:** Spot high performers vs candidates to rationalize.

**Fail / fix:** Empty → run catalog build + ensure sold qty > 0 rows exist.

### 4.4 Estoque (`03_inventory.py`)

**What:** Alerts (crítico / baixo / OK), turnover classes, reorder-oriented tables; links to utilities in `inventory_ops`.

**Why:** Reduce stockouts and overstocks.

**How to use:** Read red banner first; sort by alert severity.

**Fail / fix:** “Preencha `inventory_TEMPLATE.csv`…” → populate inventory path then ingest pipeline.

[SCREENSHOT: Inventory Alerts]

### 4.5 Operações Diárias (`04_daily_ops.py`)

**What:** Enter sales into **`data/raw/daily_sales_TEMPLATE.csv`** (append), rebuild **`daily_sales.parquet`**, optional inventory decrement, sync hooks toward Excel daily ops when master exists.

**Why:** Capture sales the same day without waiting for a full POS export.

**Caution:** Duplicates possible if you both import Eleve JSON and manually re-enter the same sales — coordinate one source of truth per day.

### 4.6 Categorias (`05_categories.py`)

**What:** View/filter products; reassign categories; writes back to **`product_catalog_categorized.csv`** (and DuckDB-related flow).

**Why:** Clean reporting dimensions.

**Fail / fix:** Missing CSV → run `categorize_products` step from refresh.

### 4.7 Exportar Excel (`06_export_excel.py`)

**What:** Pick sheets → generate **`FuloFilo_Report_*.xlsx`** via `build_report` → download.

**Why:** Email-ready artifact.

**Fail / fix:** Generation error → check Parquet presence.

[SCREENSHOT: Export Report]

---

## 5. Common Tasks

### 5.1 Edit Excel data (target workflow)

**Objective:** Update catalog, stock, sales, cashflow, categories.

| Step | Detail |
|------|--------|
| 1 | `open data/excel/FuloFilo_Master.xlsx` (when present) |
| 2 | Edit one sheet at a time; save |
| 3 | `bash scripts/sync_excel.sh` |
| 4 | Relaunch or refresh browser |

**Expected outcome:** Dashboard reflects new numbers.

**Common mistake:** Leaving workbook open on another Mac without saving — sync reads disk state only.

[SCREENSHOT: Excel Master]

### 5.2 Edit raw JSON / CSV (current repo)

**Objective:** Refresh from Eleve export.

| Step | Detail |
|------|--------|
| 1 | Place export as `data/raw/dashboard_data.json` or use Inbox automation |
| 2 | `./scripts/refresh_data.sh` |
| 3 | Check `logs/refresh.log` |

**Validation:** Log lines end with “Refresh complete”.

[SCREENSHOT: Sync Success]

### 5.3 Run sync / refresh

| Command | When |
|---------|------|
| `./scripts/refresh_data.sh` | After JSON/catalog changes (implemented) |
| `bash scripts/sync_excel.sh` | After Excel master edits |

### 5.4 Open dashboard

| Method | Command / action |
|--------|------------------|
| Terminal | `./scripts/launch_app.sh` |
| Finder | `FuloFilo.command` |

**URL:** `http://127.0.0.1:8501`

### 5.5 Export reports

| Path | Action |
|------|--------|
| In app | **Exportar Excel** → select tabs → **Gerar** → **Baixar** |
| CLI | `uv run python excel/build_report.py` |

---

## 6. Real Examples

### Example A — Monday opening checklist

1. `open data/excel/FuloFilo_Master.xlsx` (or verify JSON export date)  
2. `./scripts/refresh_data.sh`  
3. `./scripts/launch_app.sh`  
4. Visão Geral → confirm revenue matches expectation  
5. Estoque → resolve 🔴 itens  

### Example B — Promote “Hidden Gems”

1. **Matriz de Margem** → filter quadrant Hidden Gems  
2. Cross-check **Análise ABC** — if class C but high margin, test small campaign  
3. Track next week in **Operações Diárias** or POS export  

### Example C — Month-end pack

1. Refresh data  
2. **Exportar Excel** with all sheets  
3. Archive file with date in filename (default pattern `FuloFilo_Report_*.xlsx`)  

---

## 7. Tips & Best Practices

- Refresh **before** meetings so charts match reality.  
- Never hand-edit **`data/parquet/`** — regenerate.  
- Keep **SKU** discipline: blank SKUs in sales break KPIs (use strict sync when policy requires).  
- Use **Meta** sheet (Excel model) for schema version notes when available.  
- Prefer **`FuloFilo.command`** on Mac if teammates forget `uv sync` — it can heal the venv.  
- Rotate **`logs/`** if disk space is tight.  

---

## 8. Troubleshooting

| Problem | What it means | What to do |
|---------|---------------|------------|
| “venv not found” | Dependencies not installed | `uv sync` |
| Blank ABC page | No catalog data | `./scripts/refresh_data.sh` |
| Inventory empty | No inventory parquet | Complete inventory source + ingest |
| Tests fail | Data drift | Read pytest message; fix catalog or categories |
| “Address already in use” | App running | Open existing tab at port 8501 |
| `sync_excel` exits with validation error | Workbook breaks a rule (SKU, totals, etc.) | Fix sheet; read message and `data/excel/source_sync_status.json` |

---

## 9. FAQ

**Q: Do I need the internet?**  
A: Not for local dashboard after install. Initial `uv sync` may need network for packages.

**Q: Can two people edit the Excel master at once?**  
A: Not recommended — last save wins.

**Q: What is the source of truth?**  
A: Target: **`FuloFilo_Master.xlsx`**. Current repo: often **`dashboard_data.json`** + ETL outputs.

**Q: How do I know sync worked?**  
A: Logs in **`logs/refresh.log`**; KPIs update; pytest passes.

**Q: Is my data sent to the cloud?**  
A: Core path is local. Streamlit Cloud would be a separate deployment choice.

---

## 10. Power User Tips

- Run **`uv run python -m pytest tests/test_pipeline.py -v`** before month-end closes.  
- Use **`get_data_mtime`** pattern awareness: any Parquet rewrite refreshes Streamlit cache on reload.  
- Explore **`core/`** modules for decision tags and weekly report helpers on margin page.  
- For automation, macOS Shortcuts can call **`refresh_data.sh`** when inbox JSON appears (script already mentions Inbox).  
- DuckDB uses **`/tmp/duckdb_fulofilo`** — if security policy clears `/tmp` aggressively, watch for rare temp errors.  

---

## 11. Daily / Weekly Routine

| When | Task |
|------|------|
| **Daily** | Refresh data; scan Estoque; record manual sales if needed |
| **Weekly** | Review ABC shifts; adjust categories; export snapshot |
| **Monthly** | Archive Excel report; reconcile cashflow sheet (Excel model); run full pytest |

---

## 12. Final Notes

FulôFiló is built for **speed and clarity** on your Mac: keep sources clean, refresh after every edit, and choose **either** the Excel master path (`sync_excel.sh`) **or** the Eleve ETL path (`refresh_data.sh`) as your primary pipeline. For column-level detail, keep [DATA_DICTIONARY.md](DATA_DICTIONARY.md) open alongside this guide.

**Screenshot checklist**

- [SCREENSHOT: Dashboard Home]  
- [SCREENSHOT: Inventory Alerts]  
- [SCREENSHOT: Sync Success]  
- [SCREENSHOT: Excel Master]  
- [SCREENSHOT: Export Report]  
