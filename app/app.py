"""
FulôFiló Analytics Pro — Main Dashboard (HUD Edition)
======================================================
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
from app.db import get_conn, get_summary_kpis, get_abc_analysis, get_margin_matrix, get_data_mtime
from app.components.sidebar import render_sidebar, render_page_header, get_selected_period
from app.components.hud import inject_hud_css, render_hud_topbar, abc_badge, hud_plotly_layout

# ── Page Config ──────────────────────────────────────────────────────────────
_FAVICON = str(Path(__file__).resolve().parent / "assets" / "favicon.png")
st.set_page_config(
    page_title="FulôFiló Analytics Pro",
    page_icon=_FAVICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── HUD Theme ─────────────────────────────────────────────────────────────────
inject_hud_css()

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar(active_page='app.py')
render_page_header()

# ── Top Bar ───────────────────────────────────────────────────────────────────
render_hud_topbar("Visão Geral", "🌺")

# ── Load Data ─────────────────────────────────────────────────────────────────
period = get_selected_period()

@st.cache_data
def load_all(data_version: str, period: str):  # noqa: ARG001
    conn = get_conn()
    kpis = get_summary_kpis(conn, period)
    abc  = get_abc_analysis(conn, period)
    mm   = get_margin_matrix(conn, period)
    return kpis, abc, mm

kpis, abc_df, mm_df = load_all(get_data_mtime(), period)

def _f(v) -> float:
    """Safely convert any DB value (None, Decimal, int) to float."""
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0

receita, quantidade, lucro, ticket = kpis if kpis else (0, 0, 0, 0)
receita    = _f(receita)
quantidade = _f(quantidade)
lucro      = _f(lucro)
ticket     = _f(ticket)
margem_pct = (lucro / receita * 100) if receita else 0.0

# ── KPI Cards ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💰 Receita Total",  f"R$ {receita:,.2f}")
c2.metric("📦 Unidades",       f"{int(quantidade):,}")
c3.metric("📈 Lucro Bruto",    f"R$ {lucro:,.2f}")
c4.metric("📊 Margem",         f"{margem_pct:.1f}%")
c5.metric("🎫 Ticket Médio",   f"R$ {ticket:,.2f}")

st.divider()

# ── ABC Color Map (HUD neon palette) ─────────────────────────────────────────
COLORS = {
    "A": "#00FF88",  # neon green
    "B": "#FFD700",  # gold
    "C": "#FF4455",  # neon red
}

# ── Charts ────────────────────────────────────────────────────────────────────
has_sales = not abc_df.is_empty() and float(abc_df["revenue"].sum()) > 0

if has_sales:
    left, right = st.columns(2)

    with left:
        st.subheader("📊 Top 15 Produtos por Receita (ABC)")
        top15 = abc_df.head(15).to_pandas()
        fig = px.bar(
            top15, x="full_name", y="revenue",
            color="abc_class",
            color_discrete_map=COLORS,
            labels={"full_name": "Produto", "revenue": "Receita (R$)", "abc_class": "Classe"},
            title="Receita por Produto — Classificação ABC",
        )
        fig.update_layout(xaxis_tickangle=-40, showlegend=True)
        hud_plotly_layout(fig, height=420)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("🥧 Receita por Categoria")
        cat_df = abc_df.group_by("category").agg(
            pl.col("revenue").sum().alias("revenue")
        ).sort("revenue", descending=True).to_pandas()
        fig2 = px.pie(
            cat_df, values="revenue", names="category",
            color_discrete_sequence=[
                "#00D4FF","#00FF88","#FFD700","#FF4455",
                "#A78BFA","#FB923C","#34D399","#F472B6",
            ],
            title="Distribuição de Receita por Categoria",
        )
        fig2.update_traces(
            textfont_color="#E2E8F0",
            marker=dict(line=dict(color="#080C18", width=2)),
        )
        hud_plotly_layout(fig2, height=420)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── ABC Summary Table with badges ────────────────────────────────────────
    st.subheader("📋 Resumo ABC — Vendas")
    abc_summary = abc_df.group_by("abc_class").agg([
        pl.col("full_name").count().alias("full_name"),
        pl.col("revenue").sum().alias("revenue"),
        pl.col("profit").sum().alias("profit"),
    ]).sort("abc_class").to_pandas()
    abc_summary.columns = ["Classe", "Qtd Produtos", "Receita Total (R$)", "Lucro Total (R$)"]
    abc_summary["Receita Total (R$)"] = abc_summary["Receita Total (R$)"].apply(lambda x: f"R$ {x:,.2f}")
    abc_summary["Lucro Total (R$)"]   = abc_summary["Lucro Total (R$)"].apply(lambda x: f"R$ {x:,.2f}")
    abc_summary["Classe"] = abc_summary["Classe"].apply(lambda c: abc_badge(c))

    st.markdown(
        abc_summary.to_html(escape=False, index=False),
        unsafe_allow_html=True,
    )

else:
    # ── Catalog-ready state (no sales yet) ───────────────────────────────────
    st.markdown("""
<div style="
    background: rgba(0,212,255,0.06);
    border: 1px solid rgba(0,212,255,0.25);
    border-radius: 12px;
    padding: 20px 28px;
    margin-bottom: 20px;
">
<h4 style="color:#00D4FF;margin:0 0 6px;">⚡ Catálogo carregado — aguardando primeiras vendas</h4>
<p style="color:#718096;margin:0;font-size:0.9rem;">
    Registre vendas na aba <strong>DailySales</strong> do Excel master e execute
    <code>bash scripts/sync_excel.sh</code> para atualizar o dashboard.
</p>
</div>
""", unsafe_allow_html=True)

    # ── Catalog overview by type ──────────────────────────────────────────────
    conn = get_conn()
    try:
        cat_counts = conn.execute("""
            SELECT category,
                   COUNT(*)              AS skus,
                   MIN(price)            AS preco_min,
                   MAX(price)            AS preco_max,
                   ROUND(AVG(margin_pct),1) AS margem_media
            FROM products
            GROUP BY category
            ORDER BY category
        """).pl().to_pandas()

        st.subheader("👕 Catálogo de Camisetas")
        cols = st.columns(len(cat_counts))
        cat_colors = {"Camisetas Básicas":"#00D4FF","Baby Look":"#00FF88",
                      "Regatas":"#FFD700","Camisetas Infantis":"#A78BFA"}
        for col, (_, row) in zip(cols, cat_counts.iterrows()):
            color = cat_colors.get(row["category"], "#E2E8F0")
            col.markdown(f"""
<div style="
    background:rgba(255,255,255,0.04);
    border:1px solid {color}44;
    border-top:3px solid {color};
    border-radius:10px;
    padding:16px;
    text-align:center;
">
<div style="color:{color};font-size:1.6rem;font-weight:700;">{int(row['skus'])}</div>
<div style="color:#E2E8F0;font-size:0.85rem;font-weight:600;margin:4px 0;">{row['category']}</div>
<div style="color:#718096;font-size:0.75rem;">R${row['preco_min']:.0f}–R${row['preco_max']:.0f}</div>
<div style="color:{color};font-size:0.75rem;opacity:0.8;">{row['margem_media']:.1f}% margem média</div>
</div>
""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        inv = conn.execute("""
            SELECT category, SUM(current_stock) AS total_units
            FROM inventory GROUP BY category ORDER BY category
        """).pl().to_pandas()

        st.subheader("📦 Estoque Inicial")
        c1, c2, c3, c4 = st.columns(4)
        for col, (_, row) in zip([c1,c2,c3,c4], inv.iterrows()):
            col.metric(row["category"], f"{int(row['total_units']):,} un.")

    except Exception:
        st.info("Execute `bash scripts/sync_excel.sh` para carregar o catálogo.")

