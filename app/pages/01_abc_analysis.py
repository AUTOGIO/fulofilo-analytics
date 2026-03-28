from pathlib import Path as _Path
_FAVICON = str(_Path(__file__).resolve().parent.parent / 'assets' / 'favicon.png')
"""
FulôFiló — 📊 Análise ABC (HUD Edition)
=========================================
ABC Pareto with live filters, treemap, metric cards, and HUD aesthetic.
"""

import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from app.db import get_conn, get_abc_analysis, get_data_mtime
from app.components.sidebar import render_sidebar, render_page_header
from app.components.hud import inject_hud_css, render_hud_topbar, abc_badge, hud_plotly_layout

st.set_page_config(page_title="Análise ABC — FulôFiló", page_icon=_FAVICON, layout="wide")
inject_hud_css()
render_sidebar()
render_page_header()
render_hud_topbar("Análise ABC", "📊")

st.markdown("Identifica quais produtos geram **80%** da receita (A), **15%** (B) e **5%** (C).")

@st.cache_data
def load(data_version: str):  # noqa: ARG001
    conn = get_conn()
    return get_abc_analysis(conn)

df = load(get_data_mtime())
if df.is_empty():
    st.warning("Execute `etl/build_catalog.py` para gerar os dados."); st.stop()

pdf = df.to_pandas()

# HUD neon colors for ABC
COLORS = {"A": "#00FF88", "B": "#FFD700", "C": "#FF4455"}

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

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Pareto", "🌳 Treemap", "📋 Tabela"])

with tab1:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=filtered["full_name"], y=filtered["revenue"],
        marker_color=[COLORS.get(c,"#4A5568") for c in filtered["abc_live"]],
        name="Receita", hovertemplate="%{x}<br>R$ %{y:,.2f}",
        marker_line_width=0,
    ))
    fig.add_trace(go.Scatter(
        x=filtered["full_name"], y=filtered["cum_pct_live"],
        name="% Acumulado", yaxis="y2",
        line=dict(color="#FFD700", width=2.5), mode="lines+markers",
        marker=dict(size=5, color="#FFD700"),
    ))
    fig.add_hline(y=80, line_dash="dash", line_color="#FF4455", opacity=0.7,
                  annotation_text="80% — corte Classe A",
                  annotation_font_color="#FF4455")
    fig.update_layout(
        yaxis=dict(title="Receita (R$)", gridcolor="rgba(0,212,255,0.08)"),
        yaxis2=dict(title="% Acumulado", overlaying="y", side="right", range=[0,110],
                    gridcolor="rgba(0,0,0,0)"),
        xaxis_tickangle=-45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    hud_plotly_layout(fig, height=480)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    if "category" in filtered.columns:
        fig2 = px.treemap(
            filtered, path=["category","full_name"], values="revenue",
            color="abc_live", color_discrete_map=COLORS,
            title="Distribuição de Receita — Categoria → Produto",
            hover_data={"revenue": ":.2f", "qty_sold": True},
        )
        fig2.update_traces(marker_line_width=1, marker_line_color="#080C18")
        hud_plotly_layout(fig2, height=540)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Dados de categoria não disponíveis.")

with tab3:
    display = filtered[["abc_live","full_name","category","revenue","qty_sold","profit"]].copy()
    display["abc_live"] = display["abc_live"].apply(lambda c: abc_badge(c))
    display["revenue"]  = display["revenue"].apply(lambda x: f"R$ {x:,.2f}")
    display["profit"]   = display["profit"].apply(lambda x: f"R$ {x:,.2f}")
    display.columns = ["Classe","Produto","Categoria","Receita (R$)","Qtd","Lucro (R$)"]
    st.markdown(display.to_html(escape=False, index=False), unsafe_allow_html=True)

