# FulôFiló Analytics Pro — User Guide

**Operator manual** — Apple Silicon, macOS, local-first

_Last updated: 2026-04-26_

---

## 1. Introduction

**What it is:** Local BI dashboard showing sales KPIs, ABC classification, margin positioning, inventory health, daily operations, categories — plus automatic reorder alerts and Excel reports.

**Why it matters:** You decide what to stock, promote, or discontinue using the same numbers executives see — with alerts before you run out.

**How it works:** Raw sales CSVs → ETL scripts → Parquet files → DuckDB → Streamlit pages.

**Data architecture:** `products.parquet` stores **3 rows per product** (March, April, and combined). All queries filter by `period` to avoid inflated numbers.

---

## 2. Quick Start

**Objective:** See the dashboard in under five minutes.

| Step | Action | Expected outcome |
|------|--------|------------------|
| 1 | `cd /Users/giovannini_nuovo/Documents/GitHub/FuloFilo` | Shell in repo root |
| 2 | `uv sync` | `.venv` ready |
| 3 | `uv run streamlit run app/app.py` | Browser at `http://127.0.0.1:8501` |

**Validation:** Home page shows KPI cards and reorder alert banner (if any products need restocking).

---

## 3. Daily Workflow

**Objective:** Keep numbers trustworthy every selling day.

| Step | Who | Action |
|------|-----|--------|
| Morning | Operator | Launch dashboard — reorder alerts fire automatically on open |
| Morning | Operator | Review 🔴 URGENTE banner; act on reorder alerts if shown |
| During day | Operator | Record sales via **Operações Diárias** page |
| When new data arrives | Operator | Run `etl/ingest_march_april_2026.py` then `etl/build_catalog.py` |
| After changes | Operator | `python etl/sync_and_push.py` to push to GitHub + trigger cloud redeploy |
| Review | Manager | Open dashboard — ABC, Estoque, Margem |
| Optional | Analyst | **Exportar Excel** for sharing |

**Expected outcome:** Dashboard matches your latest source data; reorder alerts reflect current stock levels.

**Common mistake:** Editing Parquet manually — always regenerate from sources.

---

## 4. Dashboard Pages Explained

### 4.1 Visão Geral (`app.py`)

**What:** Top-level KPIs (receita, unidades, lucro bruto, margem %, ticket médio); reorder alert banner; top 15 products by revenue; revenue by category pie; ABC summary table.

**Period selector:** Three buttons in the sidebar — **Total (Mar–Abr 2026)**, **Março 2026**, **Abril 2026**. All charts and KPIs update to match.

**Why:** Single glance health of the business.

**Reorder banner:** Appears automatically if any products have ≤ 24 days of stock remaining. Red border = urgent products. Expand the table to see details.

**What can fail:** Empty charts if no sales in `products`.
**Fix:** Run ETL; confirm `products.parquet` has rows.

### 4.2 Análise ABC (`01_abc_analysis.py`)

**What:** Pareto view — class **A** ≈ first ~80% cumulative revenue, **B** next ~15%, **C** remainder; filters, treemap, decision hints.

**Why:** Focus time on SKUs that drive results.

**How to use:** Filter categories; read badges/decision tags.

**Fail / fix:** "Execute `etl/build_catalog.py`" → run full ETL.

### 4.3 Matriz de Margem (`02_margin_matrix.py`)

**What:** Scatter — volume vs margin %; quadrants **Stars**, **Cash Cows**, **Hidden Gems**, **Dogs**.

**Why:** Spot high performers vs candidates to rationalize.

**Fail / fix:** Empty → run catalog build + ensure sold qty > 0 rows exist.

### 4.4 Estoque (`03_inventory.py`)

**What:** Alerts (crítico / baixo / OK), turnover classes (🔥 Alto / ✅ Normal / 🐢 Baixo), reorder-oriented tables.

**Why:** Reduce stockouts and overstocks.

**How to use:** Read red alert rows first; sort by alert severity.

**Fail / fix:** Empty → confirm `inventory.parquet` exists.

### 4.5 Operações Diárias (`04_daily_ops.py`)

**What:** View and append daily sales transactions; optional inventory decrement.

**Why:** Capture same-day sales without waiting for a full POS export.

**Caution:** Avoid double-entering sales if you also import via Eleve JSON — coordinate one source of truth per day.

### 4.6 Categorias (`05_categories.py`)

**What:** View/filter products by category; revenue breakdown.

**Why:** Clean reporting dimensions.

**Fail / fix:** Empty → run `build_catalog.py`.

### 4.7 Exportar Excel (`06_export_excel.py`)

**What:** Pick sheets → generate Excel report → download.

**Why:** Email-ready artifact.

**Fail / fix:** Generation error → check Parquet presence.

### 4.8 Reorder Alert System

**What:** Automatic alert when any product is running low based on sell-through rate from March + April 2026.

**How it fires:**
1. On dashboard open (`app.py` loads) → `reorder_engine.get_alerts()` runs
2. macOS native notification pops once per session (local only, silent on Streamlit Cloud)
3. Red/amber banner appears at top of Visão Geral
4. `data/outputs/alertas_reposicao.xlsx` is auto-generated with two sheets

**Alert levels:**

| Color | Condition | Meaning |
|-------|-----------|---------|
| 🔴 URGENTE | days_remaining ≤ 12 | Order now — inside lead time |
| 🟡 ATENÇÃO | days_remaining ≤ 24 | Order soon — inside safety buffer |
| 🟢 OK | days_remaining > 24 | Stock healthy |

**Formulas:**
```
daily_rate     = qty_sold (Mar+Apr 2026) / 61 days
days_remaining = current_stock / daily_rate
suggested_qty  = ceil(daily_rate × 45 days)
```

**Configuration** (in `app/utils/reorder_engine.py`):

| Constant | Default | Meaning |
|----------|---------|---------|
| `LEAD_TIME_DAYS` | 12 | Days from order to delivery |
| `BUFFER_DAYS` | 12 | Safety buffer |
| `COVERAGE_DAYS` | 45 | Target days of stock in suggested order |

**Excel output:** `data/outputs/alertas_reposicao.xlsx` — two sheets:
- `⚠️ Reposição Urgente` — only products that need reorder now
- `📦 Todos os Produtos` — full analysis with urgency color coding

> This file is auto-generated on every dashboard load. It is **not** committed to git (gitignored). Open it directly from `data/outputs/`.

---

## 5. Common Tasks

### 5.1 Ingest new sales data

| Step | Detail |
|------|--------|
| 1 | Place CSV files in `data/raw/` as `vendas_<mes>_<ano>.csv` |
| 2 | Run `python etl/ingest_march_april_2026.py` |
| 3 | Run `python etl/build_catalog.py` |
| 4 | Refresh browser or restart Streamlit |

### 5.2 Push to GitHub / redeploy Streamlit Cloud

```bash
# Push all tracked files
python etl/sync_and_push.py

# Custom message
python etl/sync_and_push.py --message "add May 2026 sales"

# Dry run (validate only, no push)
python etl/sync_and_push.py --dry-run
```

Streamlit Cloud redeploys automatically ~60 seconds after a successful push.
URL: https://autogio-fulofilo.streamlit.app/

### 5.3 Export reorder alert spreadsheet

The file is auto-generated at `data/outputs/alertas_reposicao.xlsx` every time the dashboard loads. Open it directly:

```bash
open data/outputs/alertas_reposicao.xlsx
```

### 5.4 Export analytics report

In-app: **Exportar Excel** page → select sheets → **Gerar** → **Baixar**.

### 5.5 Change period filter

Use the three sidebar buttons: **Total**, **Março**, **Abril**. All KPIs and charts update instantly.

---

## 6. Real Examples

### Example A — Morning check

1. Open dashboard (`uv run streamlit run app/app.py`)
2. Check reorder banner at top of Visão Geral
3. If 🔴 URGENTE: open `data/outputs/alertas_reposicao.xlsx` → call supplier
4. Review ABC shifts vs previous week

### Example B — Promote "Hidden Gems"

1. **Matriz de Margem** → filter quadrant Hidden Gems
2. Cross-check **Análise ABC** — if class C but high margin, test small campaign
3. Track next week in **Operações Diárias** or POS export

### Example C — Month-end pack

1. Refresh data via ETL
2. **Exportar Excel** with all sheets
3. Archive file with date in filename
4. `python etl/sync_and_push.py --message "month-end Apr 2026"`

---

## 7. Tips & Best Practices

- Refresh **before** meetings so charts match reality.
- Never hand-edit `data/parquet/` — regenerate from sources.
- Keep **SKU** discipline: blank raw_keys in sales break JOIN logic.
- The reorder alert uses **actual March+April sell rate** — if one month was atypical, the 61-day average smooths it out.
- Individual supplier lead times can be configured per-product in a future update (groundwork is in `reorder_engine.py`).
- `data/outputs/alertas_reposicao.xlsx` is regenerated every page load — always shows current state.

---

## 8. Troubleshooting

| Problem | What it means | What to do |
|---------|---------------|------------|
| "venv not found" | Dependencies not installed | `uv sync` |
| Blank ABC page | No catalog data | Run `etl/build_catalog.py` |
| Inventory empty | No inventory parquet | Run full ETL pipeline |
| KPIs show 3× inflated values | Period filter missing in query | Report bug — `period_where()` should handle this |
| Reorder alert missing | No sales data or all stock > 24 days | Normal if stock is healthy; check `products.parquet` rows |
| macOS notification not firing | Already fired this session, or running on cloud | Restart Streamlit to reset `session_state["reorder_notified"]` |
| `sync_and_push.py` fails — "nothing to commit" | No changes staged | Normal; already up to date |
| `sync_and_push.py` push failed | Git auth issue | Confirm HTTPS remote: `git remote -v`; re-enter credentials if prompted |
| "Address already in use" | App already running | Open existing tab at port 8501 |

---

## 9. FAQ

**Q: Do I need the internet?**
A: Not for the local dashboard after install. `uv sync` needs the network for initial package download. The Streamlit Cloud version is always accessible at the public URL.

**Q: What is the source of truth for 2026 sales?**
A: `data/raw/dashboard_data_2026.json` + `vendas_marco_26.csv` + `vendas_abril_26.csv`. These are the only real data files. All pre-2026 transactions were removed in the April 2026 cleanup.

**Q: Why does my reorder alert show all products?**
A: If `current_stock` defaults to 300 for all products (inventory join miss), and daily_rate is high, many products will show low days_remaining. Update `inventory.parquet` with actual stock counts.

**Q: Is my data sent to the cloud?**
A: The Parquet data files are committed to the GitHub repo and served by Streamlit Cloud. Keep sensitive pricing/margin data in mind. The local dashboard is fully offline.

**Q: Can I change the reorder thresholds?**
A: Yes — edit `LEAD_TIME_DAYS`, `BUFFER_DAYS`, `COVERAGE_DAYS` in `app/utils/reorder_engine.py`. Per-supplier customization is planned for a future update.

---

## 10. Daily / Weekly Routine

| When | Task |
|------|------|
| **Daily** | Launch dashboard; check reorder banner; record any sales |
| **Weekly** | Review ABC shifts; check reorder alert spreadsheet; push any data updates |
| **Monthly** | Export analytics report; archive it; run full ETL with new data |

---

## 11. Final Notes

FulôFiló is built for **speed and clarity** on your Mac. Keep sources clean, run ETL after every data update, and use the reorder alert system proactively — it's calculating days of runway for every product automatically.

For column-level detail, see [DATA_DICTIONARY.md](DATA_DICTIONARY.md).
For project structure, see [README.md](README.md).
