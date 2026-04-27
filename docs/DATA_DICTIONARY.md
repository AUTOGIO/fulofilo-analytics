# FulôFiló — Data Dictionary

_Last updated: 2026-04-27_

## 1. Source of Truth

### `data/excel/FuloFilo_Master.xlsx`

Canonical operational workbook.

Sheets:

| Sheet | Role | Key columns |
|------|------|-------------|
| `Catalog` | Product master | `sku`, `full_name`, `category`, `unit_cost`, `suggested_price`, `min_stock`, `reorder_qty` |
| `Inventory` | Current stock | `sku`, `product`, `category`, `current_stock`, `min_stock`, `reorder_qty`, `supplier`, `lead_time_days`, `notes` |
| `DailySales` | Transaction log | `Date`, `sku`, `Product`, `Quantity`, `Unit_Price`, `Total`, `Payment_Method`, `Source` |
| `Cashflow` | Cash entries | `Date`, `Type`, `Category`, `Description`, `Amount`, `Payment_Method` |
| `CategoryOverrides` | Manual category overrides | `sku`, `category`, `subcategory`, `confidence` |
| `Meta` | Workbook metadata | `key`, `value` |

## 2. Generated Read Models

### `data/parquet/products.parquet`

Current-state product analytics model.

Key columns:

- `sku`
- `slug`
- `full_name`
- `category`
- `unit_cost`
- `suggested_price`
- `min_stock`
- `reorder_qty`
- `qty_sold`
- `revenue`
- `avg_price`
- `unit_profit`
- `margin_pct`
- `profit`
- `cum_revenue`
- `cum_pct`
- `abc_class`

Notes:

- `price` is exposed in DuckDB as a compatibility alias from `suggested_price`.
- No active period-slice architecture is emitted by `sync_excel.py`.

### `data/parquet/inventory.parquet`

Generated inventory read model.

Key columns:

- `slug`
- `sku`
- `product`
- `category`
- `current_stock`
- `min_stock`
- `reorder_qty`

### `data/parquet/daily_sales.parquet`

Generated sales read model.

Key columns:

- `Date`
- `Product`
- `Quantity`
- `Unit_Price`
- `Total`
- `Payment_Method`
- `Source`

### `data/parquet/cashflow.parquet`

Generated cashflow read model.

### `data/parquet/revenue_report.parquet`

Generated revenue summary.

### `data/parquet/quantity_report.parquet`

Generated quantity and profitability summary.

### `data/parquet/profit_report.parquet`

Generated profit summary.

### `data/fulofilo.duckdb`

Generated analytical database that registers views over the Parquet files. It is a query layer, not a source-of-truth.

### `data/raw/product_catalog.csv`

Generated CSV export of the canonical catalog/read model. It exists for inspection and compatibility, not for operational edits.

## 3. Generated Reports

### `excel/FuloFilo_Report_*.xlsx`

Generated report workbook created by `excel/build_report.py`. Read-only output for sharing.

### `data/outputs/alertas_reposicao.xlsx`

Generated reorder-analysis artifact. Read-only output.

## 4. Archived Legacy Evidence

Historical files under `data/raw/` are retained for audit trail and migration history.

Examples:

- `daily_sales_TEMPLATE.csv`
- `product_catalog_categorized.csv`
- historical sales CSV exports
- historical JSON exports

These files are not active write targets and are not part of the canonical Excel-first pipeline.
