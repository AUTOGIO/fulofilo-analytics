"""
FulôFiló — Product Categorization Engine
=========================================
Rule-based keyword categorization for Brazilian retail products.
Reads product_catalog.csv, applies pattern matching, writes
product_catalog_categorized.csv with Category/Subcategory columns.

Usage:
    python etl/categorize_products.py
    python etl/categorize_products.py --dry-run   # no file writes
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import polars as pl

ROOT     = Path(__file__).resolve().parent.parent
RAW_DIR  = ROOT / "data" / "raw"
IN_FILE  = RAW_DIR / "product_catalog.csv"
OUT_FILE = RAW_DIR / "product_catalog_categorized.csv"

# ── Category rules: (pattern_list) → (Category, Subcategory) ─────────────────
# Each entry: (keywords_list, category, subcategory)
# Match is case-insensitive substring on full_name / raw_key

CATEGORY_RULES: list[tuple[list[str], str, str]] = [
    # Laticínios
    (["leite", "iogurte", "queijo", "manteiga", "requeijão", "creme de leite",
      "nata", "muçarela", "mussarela"], "Laticínios", "Derivados do Leite"),

    # Proteínas
    (["frango", "carne", "peixe", "atum", "salmão", "tilápia", "patinho",
      "alcatra", "costela", "linguiça", "salsicha", "presunto", "peito"],
     "Proteínas", "Carnes e Pescados"),

    # Grãos e Massas
    (["arroz", "feijão", "lentilha", "grão de bico", "ervilha",
      "macarrão", "massa", "espaguete", "penne", "farinha"],
     "Grãos e Massas", "Básicos"),

    # Bebidas Alcoólicas
    (["cerveja", "vinho", "whisky", "whiskey", "vodka", "cachaça",
      "espumante", "gin", "rum", "conhaque", "prosecco"],
     "Bebidas", "Alcoólicas"),

    # Bebidas Não Alcoólicas
    (["suco", "água", "refrigerante", "isotônico", "chá gelado",
      "energético", "néctar", "limonada", "guaraná"],
     "Bebidas", "Não Alcoólicas"),

    # Higiene Pessoal
    (["shampoo", "condicionador", "sabonete", "creme", "hidratante",
      "desodorante", "perfume", "colônia", "protetor solar", "absorvente",
      "escova de dente", "pasta dental", "fio dental"],
     "Higiene", "Cuidado Pessoal"),

    # Limpeza
    (["detergente", "desinfetante", "alvejante", "amaciante", "sabão",
      "esponja", "vassoura", "rodo", "balde", "pano", "multiuso"],
     "Limpeza", "Produtos de Limpeza"),

    # Snacks e Guloseimas
    (["biscoito", "bolacha", "chocolate", "bala", "pirulito",
      "chiclete", "pipoca", "salgadinho", "chips", "wafer", "cookie"],
     "Snacks", "Guloseimas"),

    # Padaria / Mercearia
    (["pão", "torrada", "bolo", "rosca", "bisnaguinha", "croissant",
      "brioche", "azeite", "óleo", "vinagre", "molho", "ketchup",
      "mostarda", "maionese", "catchup"],
     "Mercearia", "Padaria e Condimentos"),

    # Cangas (FulôFiló specific)
    (["canga", "canga areia", "canga praia"], "Cangas", "Cangas"),

    # Nécessaires
    (["nécessaire", "necessaire", "estojo", "porta"], "Nécessaires", "Nécessaires"),

    # Kits
    (["kit", "conjunto", "combo"], "Kits", "Kits Presentes"),

    # Decoração
    (["decoração", "regional", "artesanato", "enfeite",
      "quadro", "almofada", "tapete", "vaso"], "Decoração", "Artesanato"),

    # Vestuário e Acessórios
    (["camiseta", "blusa", "camisa", "shorts", "bermuda",
      "vestido", "saída de praia", "biquíni", "sunga",
      "chapéu", "boné", "óculos", "sandália", "chinelo"],
     "Vestuário", "Moda Praia"),

    # Papelaria
    (["caderno", "caneta", "lápis", "borracha", "régua",
      "pasta", "agenda", "bloco"], "Papelaria", "Material Escolar"),

    # Eletrônicos / Acessórios
    (["cabo", "carregador", "fone", "headphone", "capa celular",
      "película", "powerbank", "mouse", "teclado"],
     "Eletrônicos", "Acessórios"),

    # Brinquedos
    (["brinquedo", "boneca", "carrinho", "quebra-cabeça",
      "jogo", "pelúcia", "lego"], "Brinquedos", "Toys"),

    # Saúde / Farmácia
    (["vitamina", "suplemento", "proteína", "whey", "creatina",
      "remédio", "pomada", "curativo", "antisséptico"],
     "Saúde", "Suplementos e Farmácia"),

    # Papelaria
    (["embalagem", "sacola", "caixa presente", "papel de presente",
      "fita", "laço"], "Embalagens", "Embalagens Presentes"),


    # ── FulôFiló-specific product categories ────────────────────────────────

    # Roupas (clothing — the store's core category)
    (["roupa", "bata", "body", "macaquinho", "macacão", "blusa", "camiseta",
      "vestido", "shorts", "legging", "calça", "saia", "cropped",
      "regata", "polo", "infantil", "adulto", "feminino", "unissex",
      "tamanho", "t40", "t45", "t50", "t55", "t60", "t65", "xg"],
     "Vestuário", "Roupas"),

    # Bolsas e Mochilas
    (["bolsa", "mochila", "bolsinha", "bag", "eco bag", "ecobag",
      "tote", "pochete", "carteira", "porta"], "Acessórios", "Bolsas e Mochilas"),

    # Souvenirs — Canecas
    (["caneca"], "Souvenirs", "Canecas"),

    # Souvenirs — Ímãs
    (["imã", "ima ", "ímã"], "Souvenirs", "Ímãs de Geladeira"),

    # Souvenirs — Chaveiros
    (["chaveiro"], "Souvenirs", "Chaveiros"),

    # Souvenirs — Placas
    (["placa"], "Souvenirs", "Placas Decorativas"),

    # Souvenirs — Geral (fridge magnets, small items)
    (["miniatura", "souvenir", "lembrança", "presente", "brinde"],
     "Souvenirs", "Geral"),

    # Sereia / Temáticas
    (["sereia", "oxe", "nordeste", "nordestino", "regional"],
     "Temáticos", "Regional Nordestino"),
    # Alimentos Congelados
    (["congelado", "pizza congelada", "lasanha", "empanado",
      "nugget", "hambúrguer", "esfiha"], "Congelados", "Alimentos Congelados"),
]


def _match_category(name: str) -> tuple[str, str, str]:
    """Return (Category, Subcategory, Confidence) for a product name."""
    name_lower = name.lower()
    for keywords, category, subcategory in CATEGORY_RULES:
        for kw in keywords:
            if kw in name_lower:
                return category, subcategory, "high"
    # Partial / fuzzy: try single-word matches
    tokens = re.findall(r"[a-záéíóúàâêôãõüç]+", name_lower)
    for keywords, category, subcategory in CATEGORY_RULES:
        for kw in keywords:
            kw_tokens = kw.split()
            if any(t in tokens for t in kw_tokens):
                return category, subcategory, "medium"
    return "Outros", "Não Classificado", "unmatched"


def categorize(dry_run: bool = False) -> dict:
    """
    Main categorization routine.

    Args:
        dry_run: If True, parse and validate without writing output.

    Returns:
        dict with keys: total, categorized, unmatched, unmatched_names
    """
    if not IN_FILE.exists():
        print(f"[ERROR] Input file not found: {IN_FILE}", file=sys.stderr)
        print("       Run etl/build_catalog.py first to generate product_catalog.csv")
        sys.exit(1)

    df = pl.read_csv(IN_FILE)

    # Validate expected columns
    required = {"sku", "full_name"}
    missing = required - set(df.columns)
    if missing:
        print(f"[ERROR] Missing columns in {IN_FILE}: {missing}", file=sys.stderr)
        sys.exit(1)

    print(f"[categorize] Processing {df.shape[0]} products from {IN_FILE.name}...")

    # Apply categorization
    cats, subs, confs = [], [], []
    for row in df.iter_rows(named=True):
        name = str(row.get("full_name") or row.get("raw_key") or "")
        cat, sub, conf = _match_category(name)
        cats.append(cat); subs.append(sub); confs.append(conf)

    df = df.with_columns([
        pl.Series("Category",           cats),
        pl.Series("Subcategory",         subs),
        pl.Series("CategoryConfidence",  confs),
    ])

    total      = df.shape[0]
    unmatched  = df.filter(pl.col("CategoryConfidence") == "unmatched")
    n_unmatched= unmatched.shape[0]
    n_high     = (df["CategoryConfidence"] == "high").sum()
    n_medium   = (df["CategoryConfidence"] == "medium").sum()

    print(f"\n  ✅ High confidence:   {n_high:>4}  ({n_high/total:.0%})")
    print(f"  🟡 Medium confidence: {n_medium:>4}  ({n_medium/total:.0%})")
    print(f"  ❌ Unmatched:         {n_unmatched:>4}  ({n_unmatched/total:.0%})")

    if n_unmatched > 0:
        print("\n  Unmatched products (need manual review):")
        for name in unmatched["full_name"].to_list():
            print(f"    • {name}")

    if not dry_run:
        df.write_csv(OUT_FILE)
        print(f"\n[categorize] Output written → {OUT_FILE}")
    else:
        print("\n[categorize] DRY RUN — no files written.")

    return {
        "total": total,
        "categorized": total - n_unmatched,
        "unmatched": n_unmatched,
        "unmatched_pct": n_unmatched / total if total else 0,
        "unmatched_names": unmatched["full_name"].to_list(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FulôFiló product categorizer")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and validate without writing output")
    args = parser.parse_args()
    result = categorize(dry_run=args.dry_run)
    pct = result["unmatched_pct"]
    if pct >= 0.10:
        print(f"\n⚠️  {pct:.0%} unmatched (target < 10%). Add rules to CATEGORY_RULES.")
    else:
        print(f"\n✅ Categorization complete: {pct:.0%} unmatched (within target).")
