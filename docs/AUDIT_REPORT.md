# FulôFiló Analytics Pro — Repository Audit & Cleanup

**Date:** 2026-04-22
**Scope:** Conservative cleanup — no code refactor, no history rewrite
**Target repo:** https://github.com/AUTOGIO/fulofilo-analytics

---

## 1. Findings (pre-cleanup)

### Junk tracked on disk (not all in git, but cluttering the tree)
| Item | Size | Action |
|---|---|---|
| `.venv/` | 1.2 GB | Kept on disk (user's local venv), remains gitignored |
| `cf-worker/node_modules/` | 173 MB | **Removed from disk**; reinstall via `npm install` |
| `cf-worker/.wrangler/` | — | **Removed from disk** |
| `.uv-cache/` | 20 KB | **Removed from disk** |
| `.pytest_cache/` | 20 KB | **Removed from disk** |
| `.tmp/` | empty | **Removed from disk** |
| `.DS_Store` (×29) | — | **Deleted everywhere** except inside `.git/`/`.venv/` |
| `__pycache__/` (×9 outside `.venv`) | — | **Deleted everywhere** outside `.venv/` |

### Secrets
| File | Status |
|---|---|
| `.env.cloudflare` | Contains a live `CLOUDFLARE_API_TOKEN`. **Never committed** (verified via `git log --all -S 'cfut_'`). Already gitignored by `.env.*` pattern. |

**Action:** created `.env.cloudflare.example` (redacted, committed). Real file stays local and gitignored.

> ⚠️ The token value was read during the audit. Rotate it in the Cloudflare dashboard if you want full safety.

### Root-level loose files (moved into proper subfolders)
| Before | After |
|---|---|
| `WhatsApp Image 2026-03-26 at 15.09.06.jpeg` | `assets/images/whatsapp_2026-03-26_150906.jpeg` |
| `GMT.png` | `assets/images/GMT.png` |
| `regionais.pdf` | `docs/attachments/regionais.pdf` |
| `daily_sales_conversion.xlsx` | `reports/archive/daily_sales_conversion.xlsx` |
| `FuloFilo_Report_2026-03-27.xlsx` | `reports/archive/FuloFilo_Report_2026-03-27.xlsx` (now gitignored by `FuloFilo_Report_*.xlsx` rule) |
| `sales_automation_bundle.zip` | `reports/archive/sales_automation_bundle.zip` (gitignored) |

### Portuguese folder names with accents / spaces (renamed to ASCII)
| Before | After |
|---|---|
| `FF_Grafica/Apresentação/` | `FF_Grafica/apresentacao/` |
| `FF_Grafica/Suporte Gráfico/` | `FF_Grafica/suporte_grafico/` |
| `FF_Grafica/Manual da Marca/` | `FF_Grafica/manual_da_marca/` |
| `FF_Grafica/Stickers/` | `FF_Grafica/stickers/` |
| `FF_Grafica/Logotipo/` | `FF_Grafica/logotipo/` |
| `FF_Grafica/Fontes/` | `FF_Grafica/fontes/` |
| `FF_Grafica/Fontes/Cangaço/` | `FF_Grafica/fontes/cangaco/` |
| `FF_Grafica/Fontes/Gliker/` | `FF_Grafica/fontes/gliker/` |
| `FF_Grafica/Fontes/Regards/` | `FF_Grafica/fontes/regards/` |
| `FF_Grafica/gabarito-cartão-visita-1.ai` | `FF_Grafica/gabarito_cartao_visita_1.ai` |

Why: case-only and accent-containing paths break on case-sensitive Linux CI and are fragile across tools.
Code references were grepped — none were hardcoded to the old names.

### `.gitignore` gaps closed
Added missing patterns:

- `.uv-cache/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `.tox/`
- `cf-worker/.wrangler/`, top-level `node_modules/`
- `.claude/` (editor scratch), `*~`, `*.orig`
- `FuloFilo_Report_*.xlsx` at repo root (not just `excel/`)
- `reports/*.tmp.xlsx`, `sales_automation_bundle.zip`
- `*.pem`, `*.key`
- `!.env.example`, `!.env.*.example` whitelist so example files are committable
- `build/`, `dist/`, `*.egg-info/`

---

## 2. What was NOT touched (out of scope)

- `.venv/` contents (local runtime, not in git)
- `FF_Dados_Fiscais/Saida copy.xls`, `Saida-2.xls`, `Saida-3.xls` — possible real fiscal data duplicates, needs user review
- No code refactoring (Python, Streamlit, ETL untouched)
- No git history rewrite
- `uv.lock` kept on disk but gitignored per original policy

---

## 3. Recommended next steps (not executed)

1. **Rotate the Cloudflare API token** in the Cloudflare dashboard.
2. **Add CI** (`.github/workflows/ci.yml`) running `pytest` + `ruff check` on push.
3. **Add pre-commit hooks** (`pre-commit-config.yaml`) for `ruff`, `black`, `end-of-file-fixer`, `trailing-whitespace`.
4. **Consolidate docs** — `DOCUMENTATION.md` at root overlaps with `docs/`. Consider moving into `docs/` and keeping README lean.
5. **Review `FF_Dados_Fiscais` duplicates** (`Saida copy.xls`, `Saida-2.xls`, `Saida-3.xls`) — delete stale copies.
6. **Consider switching to `uv.lock` tracked** instead of ignored, for reproducible installs. Current `pyproject.toml` alone doesn't pin exact versions.

---

---

## Audit #2 — April 2026 Bug Fix & Feature Sprint

**Date:** 2026-04-26
**Scope:** Bug fixes, data cleanup, reorder alert engine, docs update

### Data Changes

| Action | Detail |
|--------|--------|
| Deleted 733 fictional rows | `daily_sales.parquet` cleared — all pre-2026 transactions removed |
| Reset all inventory to 300 units | `inventory.parquet` — 532 SKUs set to `current_stock = 300` as baseline |
| Added monthly parquets | `products_2026_03.parquet` (37 products) and `products_2026_04.parquet` (39 products) created |
| Verified real data only | Source of truth: `dashboard_data_2026.json`, `vendas_marco_26.csv`, `vendas_abril_26.csv` |

### Bugs Fixed

| Bug | Root cause | Fix |
|-----|-----------|-----|
| `BinderException` on Estoque page | `get_stock_turnover` JOINed on `p.slug` — column does not exist | Changed to `lower(i.slug) = lower(p.raw_key) AND p.period = '2026'`; broadened `except` to catch all exceptions |
| `TypeError: receita:,.2f` on Visão Geral | `period_where("ALL")` returned `WHERE period = 'ALL'` → zero rows → `SUM = NULL` | Fixed `period_where()` to return `WHERE period = '2026'` for "ALL"; added `_f()` safe float cast helper |
| `ColumnNotFoundError` on Estoque page | `03_inventory.py` tab3 used old column names `slug` and `cost` | Corrected to `raw_key` and `unit_cost`; added `.filter(pl.col("period") == "2026")` |
| Sync & Push button broken | Script ran `build_catalog.py` first (failed), then used SSH remote (no key registered) | Rewrote `etl/sync_and_push.py` as lean git push; switched remote to HTTPS permanently |
| Triple-counted KPIs | `products.parquet` has 3 rows/product; queries without period filter returned 3× values | Added `WHERE period = '2026'` to `05_categories.py`, `04_daily_ops.py`, `get_margin_matrix` |
| Reorder engine matched only 2 products | Original JOIN was `FROM inventory LEFT JOIN products` — inventory slugs (T-shirt designs) don't match product raw_keys (item types) | Reversed JOIN to `FROM products LEFT JOIN inventory`; fallback `COALESCE(i.current_stock, 300)` |

### New Features

| Feature | File | Description |
|---------|------|-------------|
| Smart reorder alert engine | `app/utils/reorder_engine.py` | Calculates days of runway per product; fires at ≤ 24-day threshold |
| macOS native notification | `reorder_engine.notify_macos()` | AppleScript popup on dashboard open (local only, no-op on cloud) |
| Dashboard reorder banner | `app/app.py` | Red/amber alert with expandable product table |
| Reorder Excel export | `reorder_engine.export_excel()` | `data/outputs/alertas_reposicao.xlsx` with HUD dark styling, auto-generated |
| Period selector (3 buttons) | `app/components/sidebar.py` | Replaced selectbox with Total / Março / Abril buttons |
| Monthly Parquet views | `app/db.py` | Registers `products_2026_03` and `products_2026_04` DuckDB views |

### Architecture Notes

- `products.parquet` intentionally stores 3 rows/product to support per-month queries without separate ETL runs.
- All queries must use `period_where()` or `period_and()` helpers from `db.py` to prevent triple-counting.
- The inventory-product JOIN gap is a known limitation: 532 inventory SKUs track T-shirt designs; 39 sold products are item categories (cangas, chaveiros, etc.). No natural join key exists. Reorder engine defaults to 300-unit stock when no inventory row matches.

---

## 4. Execution summary

```
.DS_Store removed:            29 files
__pycache__ removed:           9 dirs (outside .venv)
cf-worker/node_modules:        173 MB freed
Folders renamed (PT→ASCII):    10
Loose root files relocated:    6
.gitignore rules added:        ~20
New files:                     .env.cloudflare.example, docs/AUDIT_REPORT.md
```
