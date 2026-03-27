# FulôFiló — Data Dictionary

## Parquet Files (`data/parquet/`)

### `products.parquet` — Master product catalog with sales & profitability
| Column | Type | Description |
|--------|------|-------------|
| `sku` | String | Unique product code (zero-padded, e.g. `00088`) |
| `raw_key` | String | Raw key from Eleve Vendas export |
| `full_name` | String | Full product display name |
| `category` | String | Category from build_catalog.py rules |
| `unit_cost` | Float64 | Purchase cost per unit (R$) |
| `suggested_price` | Float64 | Recommended sell price (R$) |
| `min_stock` | Int64 | Minimum stock threshold for reorder alert |
| `reorder_qty` | Int64 | Quantity to order when restocking |
| `unit_profit` | Float64 | `suggested_price - unit_cost` (R$) |
| `margin_pct` | Float64 | `(unit_profit / suggested_price) × 100` (%) |
| `qty_sold` | Float64 | Total units sold (period) |
| `revenue` | Float64 | Total revenue = `avg_price × qty_sold` (R$) |
| `profit` | Float64 | Total profit = `unit_profit × qty_sold` (R$) |
| `avg_price` | Float64 | Weighted average selling price (R$) |
| `cum_revenue` | Float64 | Cumulative revenue (sorted desc) for Pareto |
| `cum_pct` | Float64 | `cum_revenue / total_revenue × 100` (%) |
| `abc_class` | String | `A` (top 80%), `B` (next 15%), `C` (bottom 5%) |

### `inventory.parquet` — Stock levels per SKU
| Column | Type | Description |
|--------|------|-------------|
| `sku` | String | Foreign key → products.sku |
| `product` | String | Product display name |
| `category` | String | Category |
| `current_stock` | Int32 | Units currently in stock |
| `min_stock` | Int64 | Alert threshold (from products) |
| `reorder_qty` | Int64 | Standard order quantity |
| `supplier` | String | Supplier name (manual entry) |
| `lead_time_days` | Int32 | Days from order to delivery |
| `notes` | String | Free-text notes |

### `daily_sales.parquet` — Transaction-level sales (Eleve Vendas)
| Column | Type | Description |
|--------|------|-------------|
| `Date` | Utf8 | Transaction date (YYYY-MM-DD) |
| `Product` | Utf8 | Product name |
| `Quantity` | Float64 | Units sold |
| `Unit_Price` | Float64 | Actual selling price (R$) |
| `Total` | Float64 | `Quantity × Unit_Price` (R$) |
| `Payment_Method` | Utf8 | e.g. PIX, Cartão, Dinheiro |
| `Source` | Utf8 | Data source identifier |

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

## Raw Files (`data/raw/`)

| File | Description |
|------|-------------|
| `dashboard_data.json` | Primary Eleve Vendas export (source of truth) |
| `product_catalog.csv` | Master product list with cost/price/stock params |
| `product_catalog_categorized.csv` | catalog + Category/Subcategory/Confidence columns |
| `PRODUTOS_MAIORES_RECEITAS.txt` | Top products by revenue (Eleve formatted) |
| `PRODUTOS_MAIS_LUCRATIVOS.txt` | Most profitable products (Eleve formatted) |
| `PRODUTOS_MAIORES_VENDAS_QUANTIDADE.txt` | Top products by volume |
| `*_TEMPLATE.csv` | Empty CSV templates for manual data entry |

## ABC Classification Logic

```
Sort products by revenue descending → compute cumulative %
A = products whose cumulative revenue ≤ 80%  (high priority)
B = products 80% < cumulative ≤ 95%          (medium priority)
C = products > 95%                            (low priority)
```

## Currency & Locale

- All monetary values: **Brazilian Real (R$)**
- Number format output: `R$ #,##0.00`
- Date format output: `DD/MM/YYYY`
- Internal date storage: ISO 8601 (`YYYY-MM-DD`)
