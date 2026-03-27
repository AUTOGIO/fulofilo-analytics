"""
FulôFiló — Eleve Vendas Data Ingestion
=======================================
Converts raw exports from Eleve Vendas (CSV/JSON) into optimized Parquet files.
Also builds synthetic DailySales and CashFlow skeletons for you to populate.

Run:
    uv run python etl/ingest_eleve.py
"""

from pathlib import Path
import json
import polars as pl
from datetime import date, timedelta
import random

BASE = Path(__file__).resolve().parent.parent
RAW  = BASE / "data" / "raw"
OUT  = BASE / "data" / "parquet"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. LOAD EXISTING dashboard_data.json
# ---------------------------------------------------------------------------
with open(RAW / "dashboard_data.json") as f:
    data = json.load(f)

# Revenue report
revenue = pl.DataFrame(data["revenue_report"])
quantity = pl.DataFrame(data["quantity_report"])
profit = pl.DataFrame(data["profit_report"])

print(f"📥 Loaded: {len(revenue)} revenue rows, {len(quantity)} quantity rows")

# ---------------------------------------------------------------------------
# 2. WRITE INDIVIDUAL REPORTS AS PARQUET
# ---------------------------------------------------------------------------
revenue.write_parquet(OUT / "revenue_report.parquet")
quantity.write_parquet(OUT / "quantity_report.parquet")
profit.write_parquet(OUT / "profit_report.parquet")
print("✅ revenue_report.parquet, quantity_report.parquet, profit_report.parquet")

# ---------------------------------------------------------------------------
# 3. BUILD DAILY SALES SKELETON (2024 full year)
#    This is a TEMPLATE — replace with real Eleve Vendas CSV exports
#    Format: Date, Product, Quantity, Unit_Price, Total, Payment_Method
# ---------------------------------------------------------------------------
# Generate skeleton with realistic distribution based on known annual totals
daily_sales_schema = {
    "Date": pl.Utf8,
    "Product": pl.Utf8,
    "Quantity": pl.Float64,
    "Unit_Price": pl.Float64,
    "Total": pl.Float64,
    "Payment_Method": pl.Utf8,
    "Source": pl.Utf8,
}
daily_sales_template = pl.DataFrame(schema=daily_sales_schema)
daily_sales_template.write_parquet(OUT / "daily_sales.parquet")
daily_sales_template.write_csv(RAW / "daily_sales_TEMPLATE.csv")
print("✅ daily_sales.parquet (empty template — fill with real Eleve Vendas exports)")

# ---------------------------------------------------------------------------
# 4. BUILD CASHFLOW SKELETON
#    Categories: Vendas, Fornecedores, Aluguel, Energia, Água, Marketing,
#                Embalagens, Funcionários, Impostos
# ---------------------------------------------------------------------------
cashflow_schema = {
    "Date": pl.Utf8,
    "Type": pl.Utf8,        # "Entrada" or "Saída"
    "Category": pl.Utf8,
    "Description": pl.Utf8,
    "Amount": pl.Float64,
    "Payment_Method": pl.Utf8,
}
cashflow_template = pl.DataFrame(schema=cashflow_schema)
cashflow_template.write_parquet(OUT / "cashflow.parquet")
cashflow_template.write_csv(RAW / "cashflow_TEMPLATE.csv")
print("✅ cashflow.parquet (empty template — fill with real bank/POS data)")

# ---------------------------------------------------------------------------
# 5. BUILD INVENTORY SKELETON (all 48 products)
#    Load from products.parquet if it exists, else create schema
# ---------------------------------------------------------------------------
products_path = OUT / "products.parquet"
if products_path.exists():
    products = pl.read_parquet(products_path)
    inventory = products.select([
        pl.col("sku"),
        pl.col("full_name").alias("product"),
        pl.col("category"),
        pl.lit(0).alias("current_stock"),   # ← fill with real counts
        pl.col("min_stock"),
        pl.col("reorder_qty"),
        pl.lit("").alias("supplier"),
        pl.lit(7).alias("lead_time_days"),
        pl.lit("").alias("notes"),
    ])
    inventory.write_parquet(OUT / "inventory.parquet")
    inventory.write_csv(RAW / "inventory_TEMPLATE.csv")
    print(f"✅ inventory.parquet: {len(inventory)} products (fill current_stock with real counts)")
else:
    print("⚠️  products.parquet not found — run build_catalog.py first")

print("\n🏁 Ingestion complete. Next: run build_catalog.py, then start Streamlit.")
