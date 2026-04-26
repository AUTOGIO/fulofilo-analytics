# FulôFiló — Data Dictionary

_Last updated: 2026-04-26_

## Parquet Files (`data/parquet/`)

### `products.parquet` — Master product catalog with sales & profitability

Contains **3 rows per product** — one row per period (`2026-03`, `2026-04`, `2026`).
Always filter by `period` in queries to avoid triple-counting.

| Column | Type | Description |
|--------|------|-------------|
| `sku` | String | Unique product code (zero-padded, e.g. `00088`) |
| `raw_key` | String | Raw key from Eleve Vendas export (join key with inventory) |
| `full_name` | String | Full product display name |
| `category` | String | Category from build_catalog.py rules |
| `unit_cost` | Float64 | Purchase cost per unit (R$) |
| `suggested_price` | Float64 | Recommended sell price (R$) |
| `min_stock` | Int64 | Minimum stock threshold |
| `reorder_qty` | Int64 | Quantity to order when restocking |
| `unit_profit` | Float64 | `suggested_price - unit_cost` (R$) |
| `margin_pct` | Float64 | `(unit_profit / suggested_price) × 100` (%) |
| `qty_sold` | Float64 | Total units sold (within the period) |
| `revenue` | Float64 | Total revenue = `avg_price × qty_sold` (R$) |
| `profit` | Float64 | Total profit = `unit_profit × qty_sold` (R$) |
| `avg_price` | Float64 | Weighted average selling price (R$) |
| `cum_revenue` | Float64 | Cumulative revenue (sorted desc) for Pareto |
| `cum_pct` | Float64 | `cum_revenue / total_revenue × 100` (%) |
| `abc_class` | String | `A` (top 80%), `B` (next 15%), `C` (bottom 5%) |
| `abc_score` | Float64 | Weighted rank used to order ABC table |
| `period` | String | Period key: `2026-03`, `2026-04`, or `2026` (Mar–Apr combined) |

### `products_2026_03.parquet` — March 2026 products (37 products)

Subset of `products.parquet` filtered to `period = '2026-03'`. Registered as
DuckDB view `products_2026_03`.

### `products_2026_04.parquet` — April 2026 products (39 products)

Subset of `products.parquet` filtered to `period = '2026-04'`. Registered as
DuckDB view `products_2026_04`.

### `inventory.parquet` — Stock levels per SKU (532 SKUs)

| Column | Type | Description |
|--------|------|-------------|
| `slug` | String | Join key → `products.raw_key` (lowercase match) |
| `product` | String | Product display name |
| `category` | String | Category |
| `current_stock` | Int32 | Units currently in stock (initialized to 300 each) |
| `min_stock` | Int64 | Alert threshold |
| `reorder_qty` | Int64 | Standard reorder quantity |

> **Note:** The 532 inventory SKUs track individual T-shirt designs; the
> ~39 sold products in `products` are item types (cangas, chaveiros, etc.).
> The join on `lower(slug) = lower(raw_key)` may not always match — the
> reorder engine defaults to 300 units when no inventory row is found.

### `daily_sales.parquet` — Transaction-level sales (currently empty)

| Column | Type | Description |
|--------|------|-------------|
| `Date` | Utf8 | Transaction date (YYYY-MM-DD) |
| `Product` | Utf8 | Product name |
| `Quantity` | Float64 | Units sold |
| `Unit_Price` | Float64 | Actual selling price (R$) |
| `Total` | Float64 | `Quantity × Unit_Price` (R$) |
| `Payment_Method` | Utf8 | e.g. PIX, Cartão, Dinheiro |
| `Source` | Utf8 | Data source identifier |

> **Note:** Cleared in April 2026 cleanup — all 733 fictional rows removed.
> Use `Operações Diárias` page to append real daily transactions.

### `cashflow.parquet` — Cash in/out entries

| Column | Type | Description |
|--------|------|-------------|
| `Date` | Utf8 | Transaction date (YYYY-MM-DD) |
| `Type` | Utf8 | `Receita` or `Despesa` |
| `Category` | Utf8 | e.g. Vendas, Fornecedores, Aluguel |
| `Description` | Utf8 | Free-text description |
| `Amount` | Float64 | Absolute value in R$ |
| `Payment_Method` | Utf8 | PIX, Cartão, Boleto, etc. |

### `revenue_report.parquet` — Aggregated revenue by product

| Column | Type | Description |
|--------|------|-------------|
| `item` | String | Product name (from Eleve export) |
| `quantity` | Float64 | Total units sold |
| `revenue` | Float64 | Total revenue (R$) |

### `profit_report.parquet` — Profitability by product

| Column | Type | Description |
|--------|------|-------------|
| `code` | String | Internal product code |
| `item` | String | Product name |
| `quantity` | Float64 | Units sold |
| `total` | Float64 | Total profit (R$) |

### `quantity_report.parquet` — Volume + margin summary

| Column | Type | Description |
|--------|------|-------------|
| `cost` | Float64 | Total cost of goods sold (R$) |
| `item` | String | Product name |
| `profit` | Float64 | Total profit (R$) |
| `quantity` | Float64 | Units sold |
| `revenue` | Float64 | Total revenue (R$) |

---

## Raw Files (`data/raw/`)

| File | Description |
|------|-------------|
| `dashboard_data.json` | Legacy Eleve Vendas export (pre-2026) |
| `dashboard_data_2026.json` | **Primary 2026 source of truth** (Mar+Apr combined) |
| `vendas_marco_26.csv` | March 2026 daily sales CSV |
| `vendas_abril_26.csv` | April 2026 daily sales CSV |
| `product_catalog.csv` | Master product list with cost/price/stock params |
| `product_catalog_categorized.csv` | catalog + Category/Subcategory/Confidence columns |

---

## ABC Classification Logic

```
Sort products by revenue descending → compute cumulative %
A = products whose cumulative revenue ≤ 80%  (high priority)
B = products 80% < cumulative ≤ 95%          (medium priority)
C = products > 95%                            (low priority)
```

---

## Period Architecture

The system stores 3 rows per product in `products.parquet`:

| `period` value | Meaning |
|---------------|---------|
| `2026-03` | March 2026 only |
| `2026-04` | April 2026 only |
| `2026` | March + April combined (default view) |

The sidebar period selector maps to these values:

| Button | `period` passed to queries |
|--------|---------------------------|
| Total (Mar–Abr 2026) | `2026` |
| Março 2026 | `2026-03` |
| Abril 2026 | `2026-04` |

**Always filter queries with `WHERE period = '...'`** to avoid triple-counting KPIs.
The `period_where()` and `period_and()` helpers in `app/db.py` handle this automatically.

---

## Reorder Engine Configuration (`app/utils/reorder_engine.py`)

| Constant | Value | Meaning |
|----------|-------|---------|
| `SALES_PERIOD_DAYS` | 61 | Mar 1 – Apr 30, 2026 (reference window) |
| `LEAD_TIME_DAYS` | 12 | Default supplier lead time (days) |
| `BUFFER_DAYS` | 12 | Safety buffer (days) |
| `ALERT_THRESHOLD` | 24 | `LEAD_TIME + BUFFER` — triggers reorder alert |
| `COVERAGE_DAYS` | 45 | Target coverage window for suggested order qty |

**Core formulas:**

```
daily_rate      = qty_sold / SALES_PERIOD_DAYS
days_remaining  = current_stock / daily_rate
ALERT when:     days_remaining ≤ ALERT_THRESHOLD (24 days)
suggested_qty   = ceil(daily_rate × COVERAGE_DAYS)
```

**Outputs:**
- 🔴 URGENTE: `days_remaining ≤ LEAD_TIME_DAYS` (≤ 12 days)
- 🟡 ATENÇÃO: `days_remaining ≤ ALERT_THRESHOLD` (≤ 24 days)
- Dashboard banner (red/amber) on Visão Geral page
- macOS native notification (once per session, local only)
- `data/outputs/alertas_reposicao.xlsx` (auto-generated, gitignored)

---

## DuckDB Views (registered at startup in `app/db.py`)

| View name | Source file |
|-----------|-------------|
| `products` | `products.parquet` |
| `products_2026` | `products_2026.parquet` |
| `products_2026_03` | `products_2026_03.parquet` |
| `products_2026_04` | `products_2026_04.parquet` |
| `sales` | `daily_sales.parquet` |
| `inventory` | `inventory.parquet` |
| `cashflow` | `cashflow.parquet` |

---

## Currency & Locale

- All monetary values: **Brazilian Real (R$)**
- Number format output: `R$ #,##0.00`
- Date format output: `DD/MM/YYYY`
- Internal date storage: ISO 8601 (`YYYY-MM-DD`)
