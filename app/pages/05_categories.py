"""
FulôFiló — 🏷️ Category Manager (Page 5)
=========================================
Interactive product category management:
- View/filter all products with their Category/Subcategory
- Inline reassignment via dropdowns
- Unmatched products quick-assign section
- Sync changes back to CSV and DuckDB
"""

import sys
from pathlib import Path

import polars as pl
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from app.db import get_conn

RAW_DIR   = ROOT / "data" / "raw"
CAT_FILE  = RAW_DIR / "product_catalog_categorized.csv"
BASE_FILE = RAW_DIR / "product_catalog.csv"

st.set_page_config(page_title="Categorias — FulôFiló", page_icon="🏷️", layout="wide")

st.markdown("## 🏷️ Gerenciador de Categorias")
st.caption("Visualize, filtre e reassigne categorias de produtos. Mudanças são salvas no CSV e no DuckDB.")

# ── Load data ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_categorized() -> pl.DataFrame:
    if CAT_FILE.exists():
        return pl.read_csv(CAT_FILE)
    elif BASE_FILE.exists():
        return pl.read_csv(BASE_FILE)
    return pl.DataFrame()

df = load_categorized()

if df.is_empty():
    st.error("Arquivo product_catalog.csv não encontrado. Execute `etl/build_catalog.py` primeiro.")
    st.stop()

# Ensure Category columns exist
for col in ["Category", "Subcategory", "CategoryConfidence"]:
    if col not in df.columns:
        df = df.with_columns(pl.lit("Não Classificado").alias(col))

ALL_CATEGORIES = sorted([
    "Acessórios", "Bebidas", "Cangas", "Congelados", "Decoração",
    "Eletrônicos", "Embalagens", "Grãos e Massas", "Higiene",
    "Kits", "Laticínios", "Limpeza", "Mercearia", "Nécessaires",
    "Outros", "Papelaria", "Proteínas", "Saúde", "Snacks",
    "Souvenirs", "Temáticos", "Vestuário",
])
ALL_SUBCATEGORIES = sorted([
    "Aloólicas", "Acessórios", "Bolsas e Mochilas", "Básicos",
    "Canecas", "Cangas", "Carnes e Pescados", "Cuidado Pessoal",
    "Chaveiros", "Derivados do Leite", "Geral", "Guloseimas",
    "Ímãs de Geladeira", "Kits Presentes", "Material Escolar",
    "Não Alcoólicas", "Não Classificado", "Nécessaires",
    "Padaria e Condimentos", "Placas Decorativas", "Produtos de Limpeza",
    "Regional Nordestino", "Roupas", "Suplementos e Farmácia",
    "Toys", "Utensílios",
])

# ── Sidebar filters ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Filtros")
    cats_avail   = ["Todas"] + sorted(df["Category"].unique().to_list())
    sel_cat      = st.selectbox("Categoria", cats_avail)
    conf_avail   = ["Todas"] + sorted(df["CategoryConfidence"].unique().to_list())
    sel_conf     = st.selectbox("Confiança", conf_avail)
    search_term  = st.text_input("Buscar produto", placeholder="Digite parte do nome...")

    st.divider()
    st.markdown("### ⚡ Ações")
    if st.button("🔄 Re-executar Auto-Categorização"):
        import subprocess
        result = subprocess.run(
            [str(ROOT / ".venv/bin/python3"), str(ROOT / "etl/categorize_products.py")],
            capture_output=True, text=True
        )
        st.code(result.stdout + result.stderr)
        st.cache_data.clear()
        st.rerun()

# ── Apply filters ─────────────────────────────────────────────────────────────
view = df.clone()
if sel_cat  != "Todas":  view = view.filter(pl.col("Category")           == sel_cat)
if sel_conf != "Todas":  view = view.filter(pl.col("CategoryConfidence") == sel_conf)
if search_term:          view = view.filter(pl.col("full_name").str.contains(search_term, literal=False))

# ── Summary cards ──────────────────────────────────────────────────────────────
total = df.shape[0]
n_high    = (df["CategoryConfidence"] == "high").sum()
n_medium  = (df["CategoryConfidence"] == "medium").sum()
n_unmatched = (df["CategoryConfidence"] == "unmatched").sum()
n_cats    = df["Category"].n_unique()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total SKUs",        total)
c2.metric("✅ Alta confiança", n_high,   delta=f"{n_high/total:.0%}")
c3.metric("🟡 Média",         n_medium, delta=f"{n_medium/total:.0%}")
c4.metric("❌ Não classificado", n_unmatched,
          delta=f"{n_unmatched/total:.0%}", delta_color="inverse")
c5.metric("Categorias únicas", n_cats)

st.divider()

# ── Unmatched alert ────────────────────────────────────────────────────────────
unmatched_df = df.filter(pl.col("CategoryConfidence") == "unmatched")
if not unmatched_df.is_empty():
    with st.expander(f"⚠️ {unmatched_df.shape[0]} produtos SEM categorização — clique para atribuir", expanded=True):
        st.caption("Selecione Categoria e Subcategoria para cada produto e clique em Salvar.")
        edits = {}
        for row in unmatched_df.iter_rows(named=True):
            sku = row["sku"]
            col_a, col_b, col_c = st.columns([3, 2, 2])
            col_a.markdown(f"**{row['full_name']}** `{sku}`")
            new_cat = col_b.selectbox("Categoria", ALL_CATEGORIES,
                                       key=f"cat_{sku}", index=ALL_CATEGORIES.index("Outros"))
            new_sub = col_c.selectbox("Subcategoria", ALL_SUBCATEGORIES,
                                       key=f"sub_{sku}", index=ALL_SUBCATEGORIES.index("Não Classificado"))
            edits[sku] = (new_cat, new_sub)

        if st.button("💾 Salvar atribuições manuais"):
            updated = df.clone().to_pandas()
            for sku, (cat, sub) in edits.items():
                mask = updated["sku"] == sku
                updated.loc[mask, "Category"]           = cat
                updated.loc[mask, "Subcategory"]        = sub
                updated.loc[mask, "CategoryConfidence"] = "manual"
            pl.from_pandas(updated).write_csv(CAT_FILE)
            st.success("✅ Categorias salvas em product_catalog_categorized.csv")
            st.cache_data.clear()
            st.rerun()

# ── Main products table ────────────────────────────────────────────────────────
st.subheader(f"📋 Produtos ({view.shape[0]} de {total})")
cols_show = [c for c in ["sku","full_name","category","Category","Subcategory","CategoryConfidence"]
             if c in view.columns]
st.dataframe(view.select(cols_show).to_pandas(), use_container_width=True, hide_index=True)

# ── Category summary ───────────────────────────────────────────────────────────
st.divider()
st.subheader("📊 Receita por Categoria (via DuckDB)")
try:
    conn = get_conn()
    cat_rev = conn.execute("""
        SELECT category, SUM(revenue) AS total_rev,
               COUNT(*) AS n_skus, AVG(margin_pct) AS avg_margin
        FROM products GROUP BY category ORDER BY total_rev DESC
    """).pl()
    if not cat_rev.is_empty():
        import plotly.express as px
        fig = px.bar(cat_rev.to_pandas(), x="category", y="total_rev",
                     title="Receita Total por Categoria",
                     labels={"total_rev":"Receita (R$)","category":"Categoria"},
                     color="avg_margin", color_continuous_scale="Greens")
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.info(f"Dados de receita não disponíveis: {e}")

# ── Export ─────────────────────────────────────────────────────────────────────
st.divider()
if CAT_FILE.exists():
    csv_bytes = CAT_FILE.read_bytes()
    st.download_button("📥 Exportar CSV categorizado", csv_bytes,
                       file_name="product_catalog_categorized.csv",
                       mime="text/csv")
