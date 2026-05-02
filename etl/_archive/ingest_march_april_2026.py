"""
FulôFiló — Ingestão de Vendas Março + Abril 2026
=================================================
Lê os dois CSVs exportados do Eleve Vendas, identifica produtos novos
(não cadastrados), registra-os com estoque inicial de 450 un, e computa
todas as vendas no sistema (dashboard_data.json + inventory.parquet).

Fluxo:
  1. Parseia vendas_marco_26.csv + vendas_abril_26.csv
  2. Agrega vendas por produto (qty, revenue, cost, profit)
  3. Mapeia itens do CSV para raw_keys do catálogo existente
  4. Produtos SEM mapeamento → novos: add em inventory + CATALOG
  5. Atualiza dashboard_data.json (soma às vendas existentes)
  6. Atualiza inventory.parquet (450 inicial - vendas p/ novos)
  7. Rebuild products.parquet via build_catalog.py

Run:
    uv run python etl/ingest_march_april_2026.py
    python etl/ingest_march_april_2026.py
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import polars as pl

BASE = Path(__file__).resolve().parent.parent
RAW  = BASE / "data" / "raw"
OUT  = BASE / "data" / "parquet"

# ── 1. Mapeamento CSV item → raw_key existente no catálogo ───────────────────
# Produtos sem entrada aqui são NOVOS e serão cadastrados automaticamente.
CSV_TO_RAW_KEY: dict[str, str] = {
    "Bata adulto":     "bata adulto",
    "Bata infantil":   "bata infantil",
    "Bata XG 65":      "bata  xg",
    "Body":            "body",
    "Regional adulto": "regional",
    "Sereia":          "sereia",
    "Placa":           "placa",
    "Ecobag":          "eco bag",
    "Necessaire":      "nécessaire stylo",
    "Porta lingerie":  "porta lingerie",
    "Caneca Ágata 20": "caneca 20",
    "Caneca Ágata 30": "caneca 30",
    "Caneca louça":    "caneca louça",
    "Chaveiro ímã 10": "chaveiro 10",
    "Imã 15":          "ima 15",
}

# ── 2. Categoria de catálogo para produtos novos ─────────────────────────────
NEW_PRODUCT_CATEGORY: dict[str, str] = {
    "Body conjunto":       "Roupas Adulto",
    "Canga elastano":      "Cangas",
    "Canga viscose":       "Cangas",
    "Color 60":            "Roupas Adulto",
    "Color XG 65":         "Roupas Adulto",
    "Macaquinho":          "Roupas Adulto",
    "Oxe adulto":          "Roupas Adulto",
    "Oxe infantil":        "Roupas Infantil",
    "Oxe conjunto":        "Roupas Adulto",
    "Oxe XG":              "Roupas Adulto",
    "Regional infantil":   "Roupas Infantil",
    "Saída praia":         "Roupas Adulto",
    "Vestido algodão":     "Roupas Adulto",
    "Bolsa 55":            "Bolsas",
    "Bolsinha 15":         "Bolsas",
    "Bolsinha 20":         "Bolsas",
    "Carteira alça":       "Bolsas",
    "Boné":                "Acessórios",
    "Boneca":              "Decoração",
    "Chaveiro 5":          "Acessórios",
    "Embalagem presente 5":  "Acessórios",
    "Embalagem presente 10": "Acessórios",
    "Placa kit 100":       "Kits",
    "Bolsa kit 125":       "Kits",
}

INITIAL_STOCK = 450


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[àáâãä]", "a", s)
    s = re.sub(r"[èéêë]", "e", s)
    s = re.sub(r"[ìíîï]", "i", s)
    s = re.sub(r"[òóôõö]", "o", s)
    s = re.sub(r"[ùúûü]", "u", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def parse_csv(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append({
                "item":     row["Item"].strip(),
                "sku":      row["SKU"].strip(),
                "category": row["Categoria"].strip(),
                "qty":      float(row["Itens vendidos"].replace(",", ".")),
                "revenue":  float(row["Vendas líquidas"].replace(",", ".")),
                "cost":     float(row["Custo das mercadorias"].replace(",", ".")),
                "profit":   float(row["Lucro bruto"].replace(",", ".")),
            })
    return rows


def aggregate_sales(rows: list[dict]) -> dict[str, dict]:
    """Aggregate by item name (sum across months)."""
    agg: dict[str, dict] = {}
    for r in rows:
        k = r["item"]
        if k not in agg:
            agg[k] = {
                "item": k, "sku": r["sku"], "category": r["category"],
                "qty": 0.0, "revenue": 0.0, "cost": 0.0, "profit": 0.0,
            }
        agg[k]["qty"]     += r["qty"]
        agg[k]["revenue"] += r["revenue"]
        agg[k]["cost"]    += r["cost"]
        agg[k]["profit"]  += r["profit"]
    return agg


def main() -> None:
    print("=" * 60)
    print("FulôFiló — Ingestão Março+Abril 2026")
    print("=" * 60)

    # ── Parse CSVs ────────────────────────────────────────────────────────────
    marco = parse_csv(RAW / "vendas_marco_26.csv")
    abril = parse_csv(RAW / "vendas_abril_26.csv")
    sales = aggregate_sales(marco + abril)
    print(f"\n📦 {len(sales)} produtos únicos nos CSVs (Março+Abril)")

    # ── Classify: existing vs new ─────────────────────────────────────────────
    existing = {k: v for k, v in sales.items() if k in CSV_TO_RAW_KEY}
    new_prods = {k: v for k, v in sales.items() if k not in CSV_TO_RAW_KEY}

    print(f"  ✅ Já cadastrados (mapeados):  {len(existing)}")
    print(f"  🆕 Novos (não cadastrados):    {len(new_prods)}")
    print()

    if new_prods:
        print("🆕 PRODUTOS NOVOS detectados:")
        for name, info in sorted(new_prods.items()):
            cat = NEW_PRODUCT_CATEGORY.get(name, "Outros")
            qty = info["qty"]
            avg_price = round(info["revenue"] / qty, 2) if qty else 0.0
            avg_cost  = round(info["cost"]    / qty, 2) if qty else 0.0
            print(f"  SKU {info['sku']:>6} | {name:<30} | {cat:<20} | "
                  f"Preço R${avg_price:>6.2f} | Custo R${avg_cost:>6.2f} | "
                  f"Vendas: {int(qty)} un")
        print()

    # ── Update dashboard_data.json ────────────────────────────────────────────
    data_path = RAW / "dashboard_data.json"
    with open(data_path, encoding="utf-8") as f:
        dashboard = json.load(f)

    # Build lookup maps (by item name → index in each report)
    rev_idx = {r["item"]: i for i, r in enumerate(dashboard["revenue_report"])}
    qty_idx = {r["item"]: i for i, r in enumerate(dashboard["quantity_report"])}
    prf_idx = {r["item"]: i for i, r in enumerate(dashboard["profit_report"])}

    added_rev = added_qty = added_prf = 0

    for csv_name, info in sales.items():
        # Resolve the key used in dashboard_data
        raw_key = CSV_TO_RAW_KEY.get(csv_name, csv_name)

        # ── revenue_report ────────────────────────────────────────────────────
        if raw_key in rev_idx:
            r = dashboard["revenue_report"][rev_idx[raw_key]]
            r["quantity"] = round(r["quantity"] + info["qty"], 3)
            r["revenue"]  = round(r["revenue"]  + info["revenue"], 2)
        else:
            dashboard["revenue_report"].append({
                "item":     raw_key,
                "quantity": info["qty"],
                "revenue":  info["revenue"],
            })
            rev_idx[raw_key] = len(dashboard["revenue_report"]) - 1
            added_rev += 1

        # ── quantity_report ───────────────────────────────────────────────────
        if raw_key in qty_idx:
            r = dashboard["quantity_report"][qty_idx[raw_key]]
            r["quantity"] = round(r["quantity"] + info["qty"], 3)
            r["revenue"]  = round(r["revenue"]  + info["revenue"], 2)
            r["cost"]     = round(r["cost"]     + info["cost"], 2)
            r["profit"]   = round(r["profit"]   + info["profit"], 2)
        else:
            dashboard["quantity_report"].append({
                "item":     raw_key,
                "quantity": info["qty"],
                "revenue":  info["revenue"],
                "cost":     info["cost"],
                "profit":   info["profit"],
            })
            qty_idx[raw_key] = len(dashboard["quantity_report"]) - 1
            added_qty += 1

        # ── profit_report ─────────────────────────────────────────────────────
        if raw_key in prf_idx:
            r = dashboard["profit_report"][prf_idx[raw_key]]
            r["quantity"] = round(r["quantity"] + info["qty"], 3)
            r["total"]    = round(r["total"]    + info["profit"], 2)
        else:
            dashboard["profit_report"].append({
                "code":     info["sku"],
                "item":     raw_key,
                "quantity": info["qty"],
                "total":    info["profit"],
            })
            prf_idx[raw_key] = len(dashboard["profit_report"]) - 1
            added_prf += 1

    # Update metadata period
    dashboard["metadata"]["period"] += " + Março-Abril/2026"

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, ensure_ascii=False, indent=2)

    print(f"💾 dashboard_data.json atualizado")
    print(f"   Linhas adicionadas — revenue: {added_rev}, quantity: {added_qty}, profit: {added_prf}")
    print()

    # ── Update inventory.parquet: add new products with 450 stock ────────────
    inv = pl.read_parquet(OUT / "inventory.parquet")
    existing_slugs = set(inv["slug"].to_list())

    new_inv_rows = []
    for csv_name, info in new_prods.items():
        raw_key   = csv_name          # new products use csv_name as raw_key
        slug      = slugify(csv_name)
        if slug in existing_slugs:
            slug += "_2026"           # avoid collision
        category  = NEW_PRODUCT_CATEGORY.get(csv_name, "Outros")
        qty_sold  = int(info["qty"])
        stock     = max(0, INITIAL_STOCK - qty_sold)  # 450 initial - already sold

        new_inv_rows.append({
            "slug":          slug,
            "product":       csv_name,
            "category":      category,
            "current_stock": stock,
            "min_stock":     20,
            "reorder_qty":   60,
        })

    if new_inv_rows:
        new_inv_df = pl.DataFrame(new_inv_rows, schema={
            "slug":          pl.String,
            "product":       pl.String,
            "category":      pl.String,
            "current_stock": pl.Int64,
            "min_stock":     pl.Int64,
            "reorder_qty":   pl.Int64,
        })
        inv_updated = pl.concat([inv, new_inv_df])
        inv_updated.write_parquet(OUT / "inventory.parquet")
        print(f"📦 inventory.parquet: +{len(new_inv_rows)} novos produtos")
        for r in new_inv_rows:
            total_sold = int(sales[r["product"]]["qty"])
            print(f"   {r['product']:<30} | estoque inicial: {INITIAL_STOCK} "
                  f"| vendas: {total_sold} | atual: {r['current_stock']}")
        print()
    else:
        print("ℹ️  Nenhum produto novo para adicionar ao inventário.")

    # ── Add new products to build_catalog.py CATALOG ─────────────────────────
    catalog_path = BASE / "etl" / "build_catalog.py"
    catalog_src  = catalog_path.read_text(encoding="utf-8")

    new_catalog_lines = []
    for csv_name, info in sorted(new_prods.items(), key=lambda x: int(x[1]["sku"])):
        qty = info["qty"]
        avg_price = round(info["revenue"] / qty, 2) if qty else 10.0
        avg_cost  = round(info["cost"]    / qty, 2) if qty else 5.0
        sku       = info["sku"]
        category  = NEW_PRODUCT_CATEGORY.get(csv_name, "Outros")
        raw_key   = csv_name

        line = (
            f'    {{"sku": "{sku}", "raw_key": "{raw_key}", '
            f'"full_name": "{csv_name}", '
            f'"category": "{category}", '
            f'"unit_cost": {avg_cost:.2f}, "suggested_price": {avg_price:.2f}, '
            f'"min_stock": 20, "reorder_qty": 60}},'
        )
        new_catalog_lines.append(line)

    if new_catalog_lines:
        block = "\n    # --- Novos produtos 2026 (ingeridos em Março-Abril) ---\n"
        block += "\n".join(new_catalog_lines) + "\n"

        # Insert before closing bracket of CATALOG list
        marker = "]  # end CATALOG"
        if marker not in catalog_src:
            # fallback: insert before the last "]" in the CATALOG block
            insert_before = '\n]\n\n# ---------------------------------------------------------------------------\n# 2.'
        else:
            insert_before = marker

        if insert_before in catalog_src:
            catalog_src = catalog_src.replace(insert_before, block + insert_before)
        else:
            # safe fallback: append before the line that starts "# 2. BUILD CATALOG"
            catalog_src = catalog_src.replace(
                "# 2. BUILD CATALOG",
                block.rstrip() + "\n]\n\n# 2. BUILD CATALOG"
            )
            # Also remove the old closing bracket that was part of CATALOG
            catalog_src = catalog_src.replace(
                "]\n\n]\n\n# 2. BUILD CATALOG",
                "]\n\n# 2. BUILD CATALOG"
            )

        catalog_path.write_text(catalog_src, encoding="utf-8")
        print(f"📝 build_catalog.py: {len(new_catalog_lines)} novos produtos adicionados ao CATALOG")
    print()

    # ── Rebuild products.parquet ──────────────────────────────────────────────
    print("🔄 Reconstruindo products.parquet via build_catalog.py...")
    result = subprocess.run(
        [sys.executable, str(BASE / "etl" / "build_catalog.py")],
        capture_output=True, text=True, cwd=str(BASE)
    )
    if result.returncode == 0:
        print(result.stdout)
    else:
        print("⚠️  Erro no build_catalog.py:")
        print(result.stderr)

    print("=" * 60)
    print("✅ Ingestão Março+Abril 2026 concluída!")
    print("=" * 60)


if __name__ == "__main__":
    main()
