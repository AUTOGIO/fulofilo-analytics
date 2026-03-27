"""
FulôFiló Analytics Pro — Main Dashboard
=========================================
Entry point for the Streamlit application.
Run: uv run streamlit run app/app.py
Access: http://localhost:8501
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import polars as pl
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db import get_conn, get_summary_kpis, get_abc_analysis, get_margin_matrix
from app.components.sidebar import render_sidebar

# ── Page Config ──────────────────────────────────────────────────────────────
from pathlib import Path as _Path
_FAVICON = str(_Path(__file__).resolve().parent / "assets" / "favicon.png")
st.set_page_config(
    page_title="FulôFiló Analytics Pro",
    page_icon=_FAVICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Brand Colors ─────────────────────────────────────────────────────────────
COLORS = {
    "yellow":      "#F2C94C",
    "green_light": "#6FCF97",
    "green_dark":  "#2D6A4F",
    "red":         "#E74C3C",
    "white":       "#FAFAFA",
    "black":       "#1A1A1A",
}

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #2D6A4F;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #888;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #2D6A4F;
    }
    div[data-testid="metric-container"] {
        background: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar(active_page='app.py')

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<p class="main-header">🌺 FulôFiló Analytics Pro</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Painel de Gestão — Visão Geral 2024</p>', unsafe_allow_html=True)

# ── Load Data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_all():
    conn = get_conn()
    kpis = get_summary_kpis(conn)
    abc  = get_abc_analysis(conn)
    mm   = get_margin_matrix(conn)
    return kpis, abc, mm

kpis, abc_df, mm_df = load_all()
receita, quantidade, lucro, ticket = kpis if kpis else (0, 0, 0, 0)
margem_pct = (lucro / receita * 100) if receita else 0

# ── KPI Cards ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💰 Receita Total",  f"R$ {receita:,.2f}",   delta=None)
c2.metric("📦 Unidades",       f"{int(quantidade):,}",  delta=None)
c3.metric("📈 Lucro Bruto",    f"R$ {lucro:,.2f}",      delta=None)
c4.metric("📊 Margem",         f"{margem_pct:.1f}%",    delta=None)
c5.metric("🎫 Ticket Médio",   f"R$ {ticket:,.2f}",     delta=None)

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
if not abc_df.is_empty():
    left, right = st.columns(2)

    with left:
        st.subheader("📊 Top 15 Produtos por Receita (ABC)")
        top15 = abc_df.head(15).to_pandas()
        color_map = {"A": COLORS["green_dark"], "B": COLORS["yellow"], "C": COLORS["red"]}
        fig = px.bar(
            top15, x="full_name", y="revenue",
            color="abc_class",
            color_discrete_map=color_map,
            labels={"full_name": "Produto", "revenue": "Receita (R$)", "abc_class": "Classe"},
            title="Receita por Produto — Classificação ABC",
        )
        fig.update_layout(xaxis_tickangle=-40, height=420, showlegend=True)
        st.plotly_chart(fig, width="stretch")

    with right:
        st.subheader("🥧 Receita por Categoria")
        cat_df = abc_df.group_by("category").agg(
            pl.col("revenue").sum().alias("revenue")
        ).sort("revenue", descending=True).to_pandas()
        fig2 = px.pie(
            cat_df, values="revenue", names="category",
            color_discrete_sequence=px.colors.qualitative.Set2,
            title="Distribuição de Receita por Categoria",
        )
        fig2.update_layout(height=420)
        st.plotly_chart(fig2, width="stretch")

    st.divider()

    # ABC Summary Table
    st.subheader("📋 Resumo ABC")
    abc_summary = abc_df.group_by("abc_class").agg([
        pl.col("full_name").count().alias("full_name"),
        pl.col("revenue").sum().alias("revenue"),
        pl.col("profit").sum().alias("profit"),
    ]).sort("abc_class").to_pandas()
    abc_summary.columns = ["Classe", "Qtd Produtos", "Receita Total (R$)", "Lucro Total (R$)"]
    abc_summary["Receita Total (R$)"] = abc_summary["Receita Total (R$)"].apply(lambda x: f"R$ {x:,.2f}")
    abc_summary["Lucro Total (R$)"] = abc_summary["Lucro Total (R$)"].apply(lambda x: f"R$ {x:,.2f}")
    st.dataframe(abc_summary, width="stretch", hide_index=True)

else:
    st.info("⚙️ **Setup necessário:** Execute `etl/build_catalog.py` para carregar os dados de produtos.")
    st.code("uv run python etl/build_catalog.py\nuv run python etl/ingest_eleve.py", language="bash")
