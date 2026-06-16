import sys
from pathlib import Path

import polars as pl
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
_FAVICON = str(Path(__file__).resolve().parent.parent / "assets" / "favicon.png")
sys.path.insert(0, str(ROOT))

from app.db import get_conn, get_data_mtime
from app.components.sidebar import render_sidebar
from app.components.hud import inject_hud_css, conf_badge, hud_plotly_layout
from app.components.terminal import page_command_header, render_terminal_css
from app.utils.source_health import render_source_health_warning

st.set_page_config(page_title="Categorias — FulôFiló", page_icon=_FAVICON, layout="wide")
inject_hud_css()
render_terminal_css()
render_sidebar()
page_command_header(
    "Category Intelligence",
    "CI / taxonomy control",
    "category signal -> margin mix -> retail assortment intelligence",
)
render_source_health_warning()

st.caption("Visualize as categorias derivadas do sync canônico.")
st.warning(
    "Atualize vendas e dados operacionais na planilha Excel canônica. "
    "Overrides de categoria nesta tela estão temporariamente desabilitados."
)

# ── Load data ──────────────────────────────────────────────────────────────────
@st.cache_data
def load_categorized(data_version: str = "") -> pl.DataFrame:  # noqa: ARG001
    pq_path = ROOT / "data" / "parquet" / "products.parquet"
    if pq_path.exists():
        return pl.read_parquet(pq_path).select(
            ["sku", "full_name", "category", "margin_pct"]
        ).rename({"category": "Category"}).with_columns([
            pl.col("sku").alias("slug"),
            pl.col("Category").alias("Subcategory"),
            pl.lit("derived").alias("CategoryConfidence"),
        ])
    return pl.DataFrame()

df = load_categorized(get_data_mtime())

if df.is_empty():
    st.error("Dados de produtos não encontrados. Verifique data/parquet/products.parquet.")
    st.stop()

# Ensure Category columns exist
for col in ["Category", "Subcategory", "CategoryConfidence"]:
    if col not in df.columns:
        df = df.with_columns(pl.lit("Não Classificado").alias(col))

ALL_CATEGORIES = sorted([
    "Acessórios", "Bebidas", "Cangas", "Cangas em Elastano", "Cangas em Algodão",
    "Congelados", "Decoração",
    "Eletrônicos", "Embalagens", "Grãos e Massas", "Higiene",
    "Kits", "Laticínios", "Limpeza", "Mercearia", "Nécessaires",
    "Outros", "Papelaria", "Proteínas", "Saúde", "Snacks",
    "Souvenirs", "Temáticos", "Vestuário",
])
ALL_SUBCATEGORIES = sorted([
    "Aloólicas", "Acessórios", "Bolsas e Mochilas", "Básicos",
    "Canecas", "Cangas", "Cangas em Elastano", "Cangas em Algodão",
    "Carnes e Pescados", "Cuidado Pessoal",
    "Chaveiros", "Derivados do Leite", "Geral", "Guloseimas",
    "Ímãs de Geladeira", "Kits Presentes", "Material Escolar",
    "Não Alcoólicas", "Não Classificado", "Nécessaires",
    "Padaria e Condimentos", "Placas Decorativas", "Produtos de Limpeza",
    "Regional Nordestino", "Roupas", "Suplementos e Farmácia",
    "Toys", "Utensílios",
])

# ── Sidebar filters ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    cats_avail   = ["Todas"] + sorted(df["Category"].unique().to_list())
    sel_cat      = st.selectbox("Categoria", cats_avail)
    conf_avail   = ["Todas"] + sorted(df["CategoryConfidence"].unique().to_list())
    sel_conf     = st.selectbox("Confiança", conf_avail)
    search_term  = st.text_input("Buscar produto", placeholder="Digite parte do nome...")

    st.divider()
    st.markdown("### Actions")
    st.button("Run Auto Categorization", disabled=True)

# ── Apply filters ─────────────────────────────────────────────────────────────
view = df.clone()
if sel_cat  != "Todas":  view = view.filter(pl.col("Category")           == sel_cat)
if sel_conf != "Todas":  view = view.filter(pl.col("CategoryConfidence") == sel_conf)
if search_term:          view = view.filter(pl.col("full_name").str.contains(search_term, literal=False))

# ── Summary cards ──────────────────────────────────────────────────────────────
total       = df.shape[0]
n_high      = (df["CategoryConfidence"] == "high").sum()
n_medium    = (df["CategoryConfidence"] == "medium").sum()
n_unmatched = (df["CategoryConfidence"] == "unmatched").sum()
n_cats      = df["Category"].n_unique()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total SKUs",           total)
c2.metric("High Confidence",    n_high,      delta=f"{n_high/total:.0%}")
c3.metric("Medium",            n_medium,    delta=f"{n_medium/total:.0%}")
c4.metric("Unclassified", n_unmatched,
          delta=f"{n_unmatched/total:.0%}", delta_color="inverse")
c5.metric("Categorias únicas",    n_cats)

st.divider()

# ── Unmatched alert ────────────────────────────────────────────────────────────
unmatched_df = df.filter(pl.col("CategoryConfidence") == "unmatched")
with st.expander("✍️ Gravar override manual", expanded=not unmatched_df.is_empty()):
    st.caption("Use a rotina automática na barra lateral para manter o restante do sistema atualizado.")
    if not unmatched_df.is_empty():
        st.caption(f"{unmatched_df.shape[0]} produto(s) sem categorização detectados no read model atual.")
    edit_source = unmatched_df if not unmatched_df.is_empty() else df
    options_df = edit_source.select(["slug", "full_name", "Category", "Subcategory"]).to_pandas()
    options = {
        f"{row['full_name']} ({row['slug']})": row
        for _, row in options_df.iterrows()
    }
    selected_label = st.selectbox("Produto", list(options.keys()))
    selected_row = options[selected_label]

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        new_cat = st.selectbox(
            "Categoria",
            ALL_CATEGORIES,
            index=ALL_CATEGORIES.index(selected_row["Category"]) if selected_row["Category"] in ALL_CATEGORIES else ALL_CATEGORIES.index("Outros"),
        )
    with col_b:
        new_sub = st.selectbox(
            "Subcategoria",
            ALL_SUBCATEGORIES,
            index=ALL_SUBCATEGORIES.index(selected_row["Subcategory"]) if selected_row["Subcategory"] in ALL_SUBCATEGORIES else ALL_SUBCATEGORIES.index("Não Classificado"),
        )
    with col_c:
        confidence = st.selectbox("Confiança", ["manual", "high", "medium"], index=0)

    st.button("💾 Salvar override manual", disabled=True)

# ── Main products table with confidence badges ─────────────────────────────────
st.markdown(f'<div class="ff-section-label">Products ({view.shape[0]} of {total})</div>', unsafe_allow_html=True)
cols_show = [c for c in ["slug","full_name","category","Category","Subcategory","CategoryConfidence"]
             if c in view.columns]
display = view.select(cols_show).to_pandas()
if "CategoryConfidence" in display.columns:
    display["CategoryConfidence"] = display["CategoryConfidence"].apply(conf_badge)
st.markdown(display.to_html(escape=False, index=False), unsafe_allow_html=True)

# ── Category summary ───────────────────────────────────────────────────────────
st.divider()
st.markdown('<div class="ff-section-label">Category Revenue via DuckDB</div>', unsafe_allow_html=True)
try:
    conn = get_conn()
    cat_rev = conn.execute("""
        SELECT category, SUM(revenue) AS total_rev,
               COUNT(*) AS n_skus, AVG(margin_pct) AS avg_margin
        FROM products
        GROUP BY category ORDER BY total_rev DESC
    """).pl()
    if not cat_rev.is_empty():
        import plotly.express as px
        fig = px.bar(
            cat_rev.to_pandas(), x="category", y="total_rev",
            title="Receita Total por Categoria",
            labels={"total_rev":"Receita (R$)","category":"Categoria"},
            color="avg_margin",
            color_continuous_scale=[[0, "#00D4FF"], [1, "#00FF88"]],
        )
        fig.update_traces(marker_line_width=0)
        hud_plotly_layout(fig, height=400)
        st.plotly_chart(fig, width="stretch")
except Exception as e:
    st.info(f"Dados de receita não disponíveis: {e}")

# ── Export ─────────────────────────────────────────────────────────────────────
st.divider()
csv_bytes = view.select(cols_show).to_pandas().to_csv(index=False).encode("utf-8")
st.download_button(
    "Export Current View",
    csv_bytes,
    file_name="categorias_visualizacao.csv",
    mime="text/csv",
)
