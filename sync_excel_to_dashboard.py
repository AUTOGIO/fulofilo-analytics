"""
FuloFilo — Sync Excel report → parquet files → DuckDB → dashboard
"""
import shutil, datetime
from pathlib import Path
import pandas as pd
import polars as pl
import duckdb

XLSX    = Path("/Users/eduardogiovannini/dev/products/FuloFilo/excel/FuloFilo_Report_2026-03-27.xlsx")
DATA    = Path("/Users/eduardogiovannini/dev/products/FuloFilo/data/parquet")
DB_PATH = Path("/Users/eduardogiovannini/dev/products/FuloFilo/data/fulofilo.duckdb")
DATA.mkdir(parents=True, exist_ok=True)

# ── 1. Read Products Catalog ───────────────────────────────────────────────────
cat = pd.read_excel(XLSX, sheet_name="Products Catalog", header=0)
cat.columns = ["sku","full_name","category","unit_cost","price","margin_pct","qty_sold","revenue","abc_class"]
cat = cat.dropna(subset=["full_name"])

# Derive slug from sku
cat["slug"] = cat["sku"].astype(str).str.zfill(5)

# Derive totals
cat["cost"]   = (cat["unit_cost"] * cat["qty_sold"]).round(2)
cat["profit"] = (cat["revenue"] * cat["margin_pct"]).round(2)

products_df = pl.from_pandas(cat[[
    "slug","full_name","category","price","qty_sold",
    "revenue","cost","profit","margin_pct","abc_class"
]])
products_df.write_parquet(DATA / "products.parquet")
print(f"✅ products.parquet — {len(products_df)} produtos")

# ── 2. Read Inventory ─────────────────────────────────────────────────────────
inv = pd.read_excel(XLSX, sheet_name="Inventory", header=0)
inv.columns = ["sku","product","category","current_stock","min_stock","reorder_qty","status","days_stock","stock_val"]
inv = inv.dropna(subset=["product"])
inv["slug"] = inv["sku"].astype(str).str.zfill(5)

inventory_df = pl.from_pandas(inv[["slug","product","category","current_stock","min_stock","reorder_qty"]])
inventory_df.write_parquet(DATA / "inventory.parquet")
print(f"✅ inventory.parquet — {len(inventory_df)} SKUs")

# ── 3. Read Cashflow ──────────────────────────────────────────────────────────
cf = pd.read_excel(XLSX, sheet_name="Cashflow", header=0)
cf.columns = ["month","saldo_inicial","receita","custo","lucro","saldo_final","runway"]
cf = cf.dropna(subset=["month"])

cashflow_df = pl.from_pandas(cf[["month","receita","custo","lucro"]])
cashflow_df.write_parquet(DATA / "cashflow.parquet")
print(f"✅ cashflow.parquet — {len(cashflow_df)} meses")

# ── 4. Rebuild daily_sales from ABC sheet (proxy — 90 days random from real products) ──
import random
random.seed(42)
today = datetime.date.today()
prod_list = cat.to_dict("records")
rows = []
for d in range(90, 0, -1):
    date = today - datetime.timedelta(days=d)
    is_wk = date.weekday() >= 5
    n = random.randint(3,10) if is_wk else random.randint(1,6)
    for _ in range(n):
        p = random.choice(prod_list)
        qty = random.randint(1,3)
        rev = round(float(p["price"]) * qty, 2)
        rows.append({"date": str(date), "slug": str(p["slug"]),
                     "category": p["category"], "qty": qty,
                     "revenue": rev, "profit": round(rev * float(p["margin_pct"]), 2)})
daily_df = pl.DataFrame(rows)
daily_df.write_parquet(DATA / "daily_sales.parquet")
print(f"✅ daily_sales.parquet — {len(daily_df)} registros (90 dias)")

# ── 5. Summary reports ────────────────────────────────────────────────────────
rev_report = products_df.group_by("category").agg([
    pl.col("revenue").sum().alias("revenue"),
    pl.col("profit").sum().alias("profit"),
    pl.col("qty_sold").sum().alias("qty_sold"),
])
rev_report.write_parquet(DATA / "revenue_report.parquet")

qty_report = products_df.select(["full_name","category","qty_sold"]).sort("qty_sold", descending=True)
qty_report.write_parquet(DATA / "quantity_report.parquet")

profit_report = products_df.select(["full_name","category","profit","margin_pct"]).sort("profit", descending=True)
profit_report.write_parquet(DATA / "profit_report.parquet")
print("✅ revenue_report, quantity_report, profit_report")

# ── 6. Rebuild DuckDB ─────────────────────────────────────────────────────────
TMP = Path("/tmp/fulofilo_sync.duckdb")
if TMP.exists():
    TMP.unlink()
conn = duckdb.connect(str(TMP))
for pq in DATA.glob("*.parquet"):
    conn.execute(f"CREATE VIEW {pq.stem} AS SELECT * FROM read_parquet('{pq}')")
    print(f"   view: {pq.stem}")
conn.close()
shutil.copy2(TMP, DB_PATH)
print(f"\n✅ fulofilo.duckdb recriado")

# ── 7. Preview ────────────────────────────────────────────────────────────────
print("\n── Top 5 por receita ──")
print(products_df.sort("revenue", descending=True)
      .select(["full_name","category","qty_sold","revenue","abc_class"]).head(5))
print(f"\nReceita total : R$ {products_df['revenue'].sum():,.2f}")
print(f"Lucro total   : R$ {products_df['profit'].sum():,.2f}")
print(f"Margem média  : {products_df['margin_pct'].mean()*100:.1f}%")
