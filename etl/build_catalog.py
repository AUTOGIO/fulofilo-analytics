"""
FulôFiló — Master Product Catalog Builder
==========================================
Reads raw dashboard_data.json, resolves all naming issues (truncated names,
clothing sizes, duplicates), enriches with categories, SKUs, cost, and
estimated inventory, then writes:
  - data/parquet/products.parquet   (main analytical table)
  - data/raw/product_catalog.csv    (human-readable master catalog)

Run:
    uv run python etl/build_catalog.py
"""

from pathlib import Path
import json
import polars as pl

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
OUT = BASE / "data" / "parquet"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. MASTER CATALOG — manually curated from raw data
#    Fields: sku, raw_key, full_name, category, unit_cost, suggested_price,
#            min_stock, reorder_qty, supplier, notes
# ---------------------------------------------------------------------------
CATALOG = [
    # --- Cangas & Tecidos ---
    {"sku": "00046", "raw_key": "Canga areia",           "full_name": "Canga Areia",              "category": "Cangas",         "unit_cost": 20.00, "suggested_price": 40.00,  "min_stock": 80, "reorder_qty": 200},
    {"sku": "00049", "raw_key": "canga 35",              "full_name": "Canga Tamanho 35",          "category": "Cangas",         "unit_cost": 15.00, "suggested_price": 35.00,  "min_stock": 10, "reorder_qty": 30},

    # --- Acessórios ---
    {"sku": "00007", "raw_key": "chaveiro 10",           "full_name": "Chaveiro R$10",             "category": "Acessórios",     "unit_cost": 6.00,  "suggested_price": 10.00,  "min_stock": 100,"reorder_qty": 300},
    {"sku": "00072", "raw_key": "chaveiro peq",          "full_name": "Chaveiro Pequeno",          "category": "Acessórios",     "unit_cost": 2.50,  "suggested_price": 6.00,   "min_stock": 20, "reorder_qty": 60},
    {"sku": "00149", "raw_key": "alça",                  "full_name": "Alça de Bolsa",             "category": "Acessórios",     "unit_cost": 4.50,  "suggested_price": 12.00,  "min_stock": 80, "reorder_qty": 200},
    {"sku": "00014", "raw_key": "ima12",                 "full_name": "Imã 12cm",                  "category": "Acessórios",     "unit_cost": 6.00,  "suggested_price": 12.00,  "min_stock": 30, "reorder_qty": 100},
    {"sku": "00065", "raw_key": "ima 15",                "full_name": "Imã 15cm",                  "category": "Acessórios",     "unit_cost": 10.00, "suggested_price": 15.00,  "min_stock": 20, "reorder_qty": 60},
    {"sku": "00056", "raw_key": "imã 15",                "full_name": "Imã 15cm (Variante)",       "category": "Acessórios",     "unit_cost": 7.00,  "suggested_price": 15.00,  "min_stock": 5,  "reorder_qty": 20},
    {"sku": "00063", "raw_key": "carteira pequena",      "full_name": "Carteira Pequena",          "category": "Acessórios",     "unit_cost": 3.50,  "suggested_price": 10.00,  "min_stock": 15, "reorder_qty": 50},

    # --- Nécessaires ---
    {"sku": "00138", "raw_key": "nécessaire stylo",      "full_name": "Nécessaire Stylo",          "category": "Nécessaires",    "unit_cost": 7.00,  "suggested_price": 15.00,  "min_stock": 150,"reorder_qty": 500},

    # --- Canecas ---
    {"sku": "00029", "raw_key": "caneca louça",          "full_name": "Caneca de Louça",           "category": "Canecas",        "unit_cost": 15.00, "suggested_price": 35.00,  "min_stock": 40, "reorder_qty": 100},
    {"sku": "00041", "raw_key": "caneca 20",             "full_name": "Caneca R$20",               "category": "Canecas",        "unit_cost": 12.00, "suggested_price": 20.00,  "min_stock": 30, "reorder_qty": 80},
    {"sku": "00033", "raw_key": "caneca 30",             "full_name": "Caneca R$30",               "category": "Canecas",        "unit_cost": 15.00, "suggested_price": 30.00,  "min_stock": 20, "reorder_qty": 60},
    {"sku": "00038", "raw_key": "caneca 35",             "full_name": "Caneca R$35",               "category": "Canecas",        "unit_cost": 16.00, "suggested_price": 35.00,  "min_stock": 10, "reorder_qty": 30},

    # --- Decoração & Placas ---
    {"sku": "00001", "raw_key": "placas",                "full_name": "Placa Decorativa (Série)",  "category": "Decoração",      "unit_cost": 6.00,  "suggested_price": 15.00,  "min_stock": 60, "reorder_qty": 150},
    {"sku": "00073", "raw_key": "placa",                 "full_name": "Placa Decorativa Avulsa",   "category": "Decoração",      "unit_cost": 6.00,  "suggested_price": 17.00,  "min_stock": 20, "reorder_qty": 60},
    {"sku": "00088", "raw_key": "regional",              "full_name": "Produto Regional",          "category": "Decoração",      "unit_cost": 26.00, "suggested_price": 50.00,  "min_stock": 80, "reorder_qty": 200},

    # --- Kits ---
    {"sku": "00030", "raw_key": "kit 65",                "full_name": "Kit Turista R$65",          "category": "Kits",           "unit_cost": 31.50, "suggested_price": 65.00,  "min_stock": 25, "reorder_qty": 80},
    {"sku": "00070", "raw_key": "kit 110",               "full_name": "Kit Turista R$110",         "category": "Kits",           "unit_cost": 55.00, "suggested_price": 110.00, "min_stock": 15, "reorder_qty": 50},
    {"sku": "00067", "raw_key": "kit mochila",           "full_name": "Kit com Mochila",           "category": "Kits",           "unit_cost": 55.00, "suggested_price": 105.00, "min_stock": 5,  "reorder_qty": 15},

    # --- Bolsas ---
    {"sku": "00031", "raw_key": "bolsa 48",              "full_name": "Bolsa R$48",                "category": "Bolsas",         "unit_cost": 20.00, "suggested_price": 48.00,  "min_stock": 20, "reorder_qty": 60},
    {"sku": "00028", "raw_key": "bolsinha sereia",       "full_name": "Bolsinha Sereia",           "category": "Bolsas",         "unit_cost": 15.00, "suggested_price": 25.00,  "min_stock": 10, "reorder_qty": 30},
    {"sku": "00020", "raw_key": "porta lingerie",        "full_name": "Porta Lingerie",            "category": "Bolsas",         "unit_cost": 8.00,  "suggested_price": 20.00,  "min_stock": 15, "reorder_qty": 50},
    {"sku": "00054", "raw_key": "eco bag",               "full_name": "Eco Bag",                   "category": "Bolsas",         "unit_cost": 12.00, "suggested_price": 25.00,  "min_stock": 25, "reorder_qty": 80},
    {"sku": "00068", "raw_key": "mochila",               "full_name": "Mochila Modelo A",          "category": "Bolsas",         "unit_cost": 26.00, "suggested_price": 65.00,  "min_stock": 10, "reorder_qty": 30},
    {"sku": "00066", "raw_key": "mochila",               "full_name": "Mochila Modelo B",          "category": "Bolsas",         "unit_cost": 50.00, "suggested_price": 85.00,  "min_stock": 5,  "reorder_qty": 15},

    # --- Roupas Adulto ---
    {"sku": "00022", "raw_key": "sereia",                "full_name": "Vestido Sereia",            "category": "Roupas Adulto",  "unit_cost": 100.00,"suggested_price": 188.00, "min_stock": 5,  "reorder_qty": 15},
    {"sku": "00011", "raw_key": "bata adulto",           "full_name": "Bata Adulto",               "category": "Roupas Adulto",  "unit_cost": 22.00, "suggested_price": 60.00,  "min_stock": 10, "reorder_qty": 30},
    {"sku": "00071", "raw_key": "bata  xg",              "full_name": "Bata Adulto XG",            "category": "Roupas Adulto",  "unit_cost": 30.00, "suggested_price": 65.00,  "min_stock": 5,  "reorder_qty": 15},
    {"sku": "00131", "raw_key": "body",                  "full_name": "Body Adulto",               "category": "Roupas Adulto",  "unit_cost": 12.00, "suggested_price": 28.00,  "min_stock": 10, "reorder_qty": 30},
    {"sku": "00064", "raw_key": "body oxe",              "full_name": "Body Oxe",                  "category": "Roupas Adulto",  "unit_cost": 15.00, "suggested_price": 35.00,  "min_stock": 10, "reorder_qty": 30},
    {"sku": "00058", "raw_key": "conjunto masc oxe",     "full_name": "Conjunto Masculino Oxe",    "category": "Roupas Adulto",  "unit_cost": 35.00, "suggested_price": 66.00,  "min_stock": 10, "reorder_qty": 30},
    {"sku": "00059", "raw_key": "macaquinho fem oxe",    "full_name": "Macaquinho Feminino Oxe",   "category": "Roupas Adulto",  "unit_cost": 35.00, "suggested_price": 55.00,  "min_stock": 8,  "reorder_qty": 25},
    {"sku": "00061", "raw_key": "macaquinho fem 40",     "full_name": "Macaquinho Feminino T40",   "category": "Roupas Adulto",  "unit_cost": 25.00, "suggested_price": 40.00,  "min_stock": 8,  "reorder_qty": 25},
    {"sku": "00044", "raw_key": "macaquinho unissex 45", "full_name": "Macaquinho Unissex T45",    "category": "Roupas Adulto",  "unit_cost": 20.00, "suggested_price": 45.00,  "min_stock": 8,  "reorder_qty": 25},
    {"sku": "00062", "raw_key": "vestido oxe 60",        "full_name": "Vestido Oxe T60",           "category": "Roupas Adulto",  "unit_cost": 24.00, "suggested_price": 50.00,  "min_stock": 8,  "reorder_qty": 25},
    {"sku": "00060", "raw_key": "vestido algodão pp a g","full_name": "Vestido Algodão PP-G",      "category": "Roupas Adulto",  "unit_cost": 25.00, "suggested_price": 50.00,  "min_stock": 10, "reorder_qty": 30},
    {"sku": "00069", "raw_key": "vestido algodão gg",    "full_name": "Vestido Algodão GG",        "category": "Roupas Adulto",  "unit_cost": 30.00, "suggested_price": 55.00,  "min_stock": 5,  "reorder_qty": 15},
    # Clothing sizes (confirmed: tamanhos de roupa)
    {"sku": "00053", "raw_key": "40",                    "full_name": "Roupa Tamanho 40",          "category": "Roupas Adulto",  "unit_cost": 20.00, "suggested_price": 40.00,  "min_stock": 8,  "reorder_qty": 20},
    {"sku": "00051", "raw_key": "45",                    "full_name": "Roupa Tamanho 45",          "category": "Roupas Adulto",  "unit_cost": 25.00, "suggested_price": 45.00,  "min_stock": 8,  "reorder_qty": 20},
    {"sku": "00055", "raw_key": "50",                    "full_name": "Roupa Tamanho 50",          "category": "Roupas Adulto",  "unit_cost": 28.00, "suggested_price": 50.00,  "min_stock": 8,  "reorder_qty": 20},
    {"sku": "00047", "raw_key": "55",                    "full_name": "Roupa Tamanho 55",          "category": "Roupas Adulto",  "unit_cost": 30.00, "suggested_price": 55.00,  "min_stock": 8,  "reorder_qty": 20},
    {"sku": "00043", "raw_key": "60",                    "full_name": "Roupa Tamanho 60",          "category": "Roupas Adulto",  "unit_cost": 30.00, "suggested_price": 60.00,  "min_stock": 5,  "reorder_qty": 15},
    {"sku": "00048", "raw_key": "65",                    "full_name": "Roupa Tamanho 65",          "category": "Roupas Adulto",  "unit_cost": 35.00, "suggested_price": 65.00,  "min_stock": 5,  "reorder_qty": 15},
    {"sku": "00153", "raw_key": "3 estágios",            "full_name": "Roupa 3 Estágios",          "category": "Roupas Adulto",  "unit_cost": 30.00, "suggested_price": 70.00,  "min_stock": 5,  "reorder_qty": 15},

    # --- Roupas Infantil ---
    {"sku": "00024", "raw_key": "infantil",              "full_name": "Roupa Infantil",            "category": "Roupas Infantil","unit_cost": 16.00, "suggested_price": 40.00,  "min_stock": 15, "reorder_qty": 40},
    {"sku": "00136", "raw_key": "bata infantil",         "full_name": "Bata Infantil",             "category": "Roupas Infantil","unit_cost": 20.00, "suggested_price": 40.00,  "min_stock": 10, "reorder_qty": 30},
    {"sku": "00057", "raw_key": "camisa infantil oxe",   "full_name": "Camisa Infantil Oxe",       "category": "Roupas Infantil","unit_cost": 35.00, "suggested_price": 58.00,  "min_stock": 8,  "reorder_qty": 25},
]

# ---------------------------------------------------------------------------
# 2. BUILD CATALOG DATAFRAME
# ---------------------------------------------------------------------------
catalog_df = pl.DataFrame(CATALOG).with_columns([
    (pl.col("suggested_price") - pl.col("unit_cost")).alias("unit_profit"),
    ((pl.col("suggested_price") - pl.col("unit_cost")) / pl.col("suggested_price") * 100)
        .round(1).alias("margin_pct"),
])

# ---------------------------------------------------------------------------
# 3. LOAD RAW SALES DATA & MERGE
# ---------------------------------------------------------------------------
with open(RAW / "dashboard_data.json") as f:
    raw = json.load(f)

revenue_df = pl.DataFrame(raw["revenue_report"])
quantity_df = pl.DataFrame(raw["quantity_report"])

# quantity_report contains both revenue and profit with full item names;
# profit_report has truncated item names that won't join, so we use quantity_report.
revenue_agg = revenue_df.group_by("item").agg([
    pl.col("quantity").sum().alias("qty_sold"),
    pl.col("revenue").sum().alias("revenue"),
])
profit_agg = quantity_df.group_by("item").agg([
    pl.col("profit").sum().alias("profit"),
])

# Merge with catalog on raw_key
products = (
    catalog_df
    .join(revenue_agg, left_on="raw_key", right_on="item", how="left")
    .join(profit_agg,  left_on="raw_key", right_on="item", how="left")
    .with_columns([
        pl.col("qty_sold").fill_null(0),
        pl.col("revenue").fill_null(0.0),
        pl.col("profit").fill_null(0.0),
        (pl.col("revenue") / pl.when(pl.col("qty_sold") == 0).then(1).otherwise(pl.col("qty_sold"))).round(2).alias("avg_price"),
    ])
    .sort("revenue", descending=True)
)

# ---------------------------------------------------------------------------
# 4. ABC CLASSIFICATION
# ---------------------------------------------------------------------------
total_revenue = products["revenue"].sum()
products = products.with_columns([
    pl.col("revenue").cum_sum().alias("cum_revenue"),
])
products = products.with_columns([
    (pl.col("cum_revenue") / total_revenue * 100).round(1).alias("cum_pct"),
    pl.when(pl.col("cum_revenue") / total_revenue <= 0.80).then(pl.lit("A"))
      .when(pl.col("cum_revenue") / total_revenue <= 0.95).then(pl.lit("B"))
      .otherwise(pl.lit("C")).alias("abc_class"),
])

# ---------------------------------------------------------------------------
# 5. WRITE OUTPUTS
# ---------------------------------------------------------------------------
products.write_parquet(OUT / "products.parquet")
products.write_csv(RAW / "product_catalog.csv")

print(f"✅ products.parquet: {len(products)} products")
print(f"✅ product_catalog.csv: {len(products)} products")
print(f"\n📊 ABC Summary:")
abc_summary = products.group_by("abc_class").agg([
    pl.len().alias("count"),
    pl.col("revenue").sum().alias("total_revenue"),
]).sort("abc_class")
print(abc_summary)
print(f"\n💰 Total Revenue: R$ {total_revenue:,.2f}")
