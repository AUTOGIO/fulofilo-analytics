"""
FulôFiló — 📊 Análise ABC (Enhanced)
=======================================
ABC Pareto with live filters, treemap, and metric cards.
"""

import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from app.db import get_conn, get_abc_analysis

st.set_page_config(page_title="Análise ABC — FulôFiló", page_icon="📊", layout="wide")
st.title("📊 Análise ABC — Classificação Pareto")
st.markdown("Identifica quais produtos geram **80%** da receita (A), **15%** (B) e **5%** (C).")

@st.cache_data(ttl=300)
def load():
    conn = get_conn()
    return get_abc_analysis(conn)

df = load()
if df.is_empty():
    st.warning("Execute `etl/build_catalog.py` para gerar os dados."); st.stop()

pdf = df.to_pandas()
COLORS = {"A": "#2D6A4F", "B": "#F2C94C", "C": "#E74C3C"}

# ── Sidebar filters ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Filtros")
    cats = ["Todas"] + sorted(pdf["category"].unique().tolist())
    cat_filter = st.selectbox("Categoria", cats)
    abc_filter = st.multiselect("Classe ABC", ["A","B","C"], default=["A","B","C"])
    min_sales  = st.toggle("Apenas produtos com ≥ 5 vendas")

# ── Apply filters & recalculate ABC live ──────────────────────────────────────
filtered = pdf.copy()
if cat_filter != "Todas": filtered = filtered[filtered["category"] == cat_filter]
filtered = filtered[filtered["abc_class"].isin(abc_filter)]
if min_sales: filtered = filtered[filtered["qty_sold"] >= 5]

total_rev = filtered["revenue"].sum()
filtered = filtered.sort_values("revenue", ascending=False).reset_index(drop=True)
filtered["cum_pct_live"] = filtered["revenue"].cumsum() / total_rev * 100 if total_rev else 0

def live_abc(cum):
    if cum <= 80:  return "A"
    if cum <= 95:  return "B"
    return "C"
filtered["abc_live"] = filtered["cum_pct_live"].apply(live_abc)

# ── Metric cards ───────────────────────────────────────────────────────────────
a_df = filtered[filtered["abc_live"]=="A"]
b_df = filtered[filtered["abc_live"]=="B"]
c_df = filtered[filtered["abc_live"]=="C"]
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Total produtos",    len(filtered))
c2.metric("🟢 Classe A",  f"{len(a_df)} produtos",  f"R$ {a_df['revenue'].sum():,.0f}")
c3.metric("🟡 Classe B",  f"{len(b_df)} produtos",  f"R$ {b_df['revenue'].sum():,.0f}")
c4.metric("🔴 Classe C",  f"{len(c_df)} produtos",  f"R$ {c_df['revenue'].sum():,.0f}")
c5.metric("Receita filtrada",  f"R$ {total_rev:,.2f}")
st.divider()

# ── Pareto bar chart ──────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Pareto", "🌳 Treemap", "📋 Tabela"])

with tab1:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=filtered["full_name"], y=filtered["revenue"],
        marker_color=[COLORS.get(c,"#999") for c in filtered["abc_live"]],
        name="Receita", hovertemplate="%{x}<br>R$ %{y:,.2f}",
    ))
    fig.add_trace(go.Scatter(
        x=filtered["full_name"], y=filtered["cum_pct_live"],
        name="% Acumulado", yaxis="y2",
        line=dict(color="#F2C94C", width=3), mode="lines+markers",
    ))
    fig.add_hline(y=80, line_dash="dash", line_color="red",
                  annotation_text="80% — corte Classe A")
    fig.update_layout(
        yaxis=dict(title="Receita (R$)"),
        yaxis2=dict(title="% Acumulado", overlaying="y", side="right", range=[0,110]),
        xaxis_tickangle=-45, height=460,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    if "category" in filtered.columns:
        fig2 = px.treemap(
            filtered, path=["category","full_name"], values="revenue",
            color="abc_live", color_discrete_map=COLORS,
            title="Distribuição de Receita — Categoria → Produto",
            hover_data={"revenue": ":.2f", "qty_sold": True},
        )
        fig2.update_layout(height=520)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Dados de categoria não disponíveis.")

with tab3:
    display = filtered[["abc_live","full_name","category","revenue","qty_sold","profit"]].copy()
    display.columns = ["Classe","Produto","Categoria","Receita (R$)","Qtd","Lucro (R$)"]
    display["Receita (R$)"] = display["Receita (R$)"].apply(lambda x: f"R$ {x:,.2f}")
    display["Lucro (R$)"]   = display["Lucro (R$)"].apply(lambda x: f"R$ {x:,.2f}")
    st.dataframe(display, use_container_width=True, hide_index=True)
