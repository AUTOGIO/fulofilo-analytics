"""
Add full March 2026 sales for all 42 real products — realistic daily patterns.
Replaces existing March entries to avoid duplicates, then appends.
"""
import random, datetime, shutil
from pathlib import Path
import polars as pl
import duckdb

random.seed(2026)

DATA    = Path("/Users/eduardogiovannini/dev/products/FuloFilo/data/parquet")
DB_PATH = Path("/Users/eduardogiovannini/dev/products/FuloFilo/data/fulofilo.duckdb")

# Load products to get real prices and margins
products = pl.read_parquet(DATA / "products.parquet").to_dicts()
prod_lookup = {p["slug"]: p for p in products}

# Category weights — Necessaire and Carteira sell more in March (gift season)
CAT_WEIGHT = {"Necessaire": 3.0, "Carteira": 2.5, "Chaveiro": 2.0, "Vestuario": 1.5, "Body": 1.0}
CATEGORY_MAP = {p["slug"]: p["category"] for p in products}

def weighted_product():
    weights = [CAT_WEIGHT.get(p["category"], 1.0) for p in products]
    return random.choices(products, weights=weights, k=1)[0]

# Generate March 2026 daily sales (2026-03-01 to 2026-03-27)
MARCH_START = datetime.date(2026, 3, 1)
MARCH_END   = datetime.date(2026, 3, 27)   # today

new_rows = []
d = MARCH_START
while d <= MARCH_END:
    is_weekend  = d.weekday() >= 5          # Sat/Sun
    is_friday   = d.weekday() == 4
    is_month_end= d.day >= 25

    # Transactions per day: higher on weekends, Fridays, end of month
    base = 8 if is_weekend else (6 if is_friday else 4)
    if is_month_end: base = int(base * 1.3)
    n_tx = random.randint(base, base + 4)

    for _ in range(n_tx):
        p   = weighted_product()
        qty = random.choices([1, 2, 3], weights=[60, 30, 10])[0]
        rev = round(p["price"] * qty, 2)
        pft = round(rev * p["margin_pct"], 2)
        pmt = random.choices(
            ["Pix", "Cartao Credito", "Dinheiro", "Cartao Debito"],
            weights=[45, 30, 15, 10]
        )[0]
        new_rows.append({
            "date":     str(d),
            "slug":     p["slug"],
            "category": p["category"],
            "qty":      qty,
            "revenue":  rev,
            "profit":   pft,
            "payment":  pmt,
        })
    d += datetime.timedelta(days=1)

march_df = pl.DataFrame(new_rows)

# Load existing sales, drop any existing March 2026 entries, then append
existing = pl.read_parquet(DATA / "daily_sales.parquet")

# Add payment column to existing if missing
if "payment" not in existing.columns:
    existing = existing.with_columns(pl.lit("Pix").alias("payment"))

# Remove existing March 2026 rows (to avoid duplicates)
existing_clean = existing.filter(~pl.col("date").str.starts_with("2026-03"))

# Combine and sort
combined = pl.concat([existing_clean, march_df], how="diagonal").sort("date")
combined.write_parquet(DATA / "daily_sales.parquet")

# Stats
march_revenue = march_df["revenue"].sum()
march_txns    = len(march_df)
daily_avg     = march_revenue / 27

print(f"✅ {march_txns} transações adicionadas (Mar 2026)")
print(f"   Receita março : R$ {march_revenue:,.2f}")
print(f"   Média diária  : R$ {daily_avg:,.2f}")
print(f"   Total no arquivo: {len(combined)} registros")

# Top 5 products this month
top = (march_df.group_by("slug")
       .agg([pl.col("revenue").sum(), pl.col("qty").sum()])
       .sort("revenue", descending=True)
       .head(5))
top = top.with_columns(
    pl.col("slug").map_elements(lambda s: prod_lookup.get(s, {}).get("full_name", s), return_dtype=pl.Utf8).alias("produto")
)
print("\nTop 5 produtos em março:")
print(top.select(["produto","qty","revenue"]))

# Payment breakdown
print("\nMix de pagamento:")
print(march_df.group_by("payment").agg(
    pl.col("revenue").sum().alias("receita"),
    pl.len().alias("transacoes")
).sort("receita", descending=True))

# Rebuild DuckDB
TMP = Path("/tmp/fulofilo_march.duckdb")
if TMP.exists(): TMP.unlink()
conn = duckdb.connect(str(TMP))
for pq in DATA.glob("*.parquet"):
    conn.execute(f"CREATE VIEW {pq.stem} AS SELECT * FROM read_parquet('{pq}')")
conn.close()
shutil.copy2(TMP, DB_PATH)
print(f"\n✅ DuckDB reconstruído com dados de março")
