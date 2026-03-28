from pathlib import Path as _Path
_FAVICON = str(_Path(__file__).resolve().parent.parent / 'assets' / 'favicon.png')
"""
FulôFiló — Matriz de Margem (HUD Edition)
==========================================
Scatter plot: X = Quantity Sold, Y = Margin %, Bubble = Revenue
Quadrants: Stars (high vol + high margin), Cash Cows, Hidden Gems, Dogs
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.db import get_conn, get_margin_matrix, get_data_mtime
from app.components.sidebar import render_sidebar, render_page_header
from app.components.hud import inject_hud_css, render_hud_topbar, hud_plotly_layout

st.set_page_config(page_title="Matriz de Margem — FulôFiló", page_icon=_FAVICON, layout="wide")
inject_hud_css()
render_sidebar()
render_page_header()
render_hud_topbar("Matriz de Margem", "💹")

st.markdown("""
Identifica o posicionamento estratégico de cada produto:
- 🌟 **Stars** (alto volume + alta margem) — prioridade máxima de estoque
- 🐄 **Cash Cows** (alto volume + margem moderada) — base do negócio
- 💎 **Hidden Gems** (baixo volume + alta margem) — potencial de crescimento
- 🐕 **Dogs** (baixo volume + baixa margem) — candidatos a descontinuação
""")

@st.cache_data
def load(data_version: str):  # noqa: ARG001
    conn = get_conn()
    return get_margin_matrix(conn)

df = load(get_data_mtime())

if df.is_empty():
    st.warning("Execute `etl/build_catalog.py` primeiro.")
    st.stop()

pdf = df.to_pandas()

# ── Filters ──────────────────────────────────────────────────────────────────
categories = ["Todas"] + sorted(pdf["category"].unique().tolist())
cat_filter = st.selectbox("Filtrar por Categoria", categories)
if cat_filter != "Todas":
    pdf = pdf[pdf["category"] == cat_filter]

# ── Scatter Plot ──────────────────────────────────────────────────────────────
st.subheader("Scatter: Volume × Margem")
fig = px.scatter(
    pdf,
    x="qty_sold",
    y="margin_pct",
    size="revenue",
    color="margin_pct",
    hover_name="full_name",
    hover_data={"category": True, "revenue": ":,.2f", "qty_sold": True, "margin_pct": ":.1f%"},
    color_continuous_scale=[
        [0.0,  "#FF4455"],
        [0.5,  "#FFD700"],
        [1.0,  "#00FF88"],
    ],
    size_max=60,
    labels={
        "qty_sold": "Quantidade Vendida",
        "margin_pct": "Margem (%)",
        "revenue": "Receita (R$)",
    },
    title="Matriz de Margem — Tamanho da bolha = Receita",
)

# Quadrant lines
med_qty    = pdf["qty_sold"].median()
med_margin = pdf["margin_pct"].median()

fig.add_vline(x=med_qty,    line_dash="dash", line_color="rgba(0,212,255,0.35)", line_width=1)
fig.add_hline(y=med_margin, line_dash="dash", line_color="rgba(0,212,255,0.35)", line_width=1)

# Quadrant annotations
font_base = dict(family="Inter, sans-serif", size=13)
fig.add_annotation(x=pdf["qty_sold"].max()*0.85, y=pdf["margin_pct"].max()*0.95,
                   text="🌟 Stars", showarrow=False,
                   font={**font_base, "color": "#00FF88"})
fig.add_annotation(x=pdf["qty_sold"].max()*0.85, y=pdf["margin_pct"].min()*1.1,
                   text="🐄 Cash Cows", showarrow=False,
                   font={**font_base, "color": "#FFD700"})
fig.add_annotation(x=pdf["qty_sold"].min()*1.5, y=pdf["margin_pct"].max()*0.95,
                   text="💎 Hidden Gems", showarrow=False,
                   font={**font_base, "color": "#00D4FF"})
fig.add_annotation(x=pdf["qty_sold"].min()*1.5, y=pdf["margin_pct"].min()*1.1,
                   text="🐕 Dogs", showarrow=False,
                   font={**font_base, "color": "#FF4455"})

fig.update_layout(coloraxis_showscale=True)
hud_plotly_layout(fig, height=560)
st.plotly_chart(fig, use_container_width=True)

# ── Top / Bottom Margin Tables ─────────────────────────────────────────────────
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏆 Top 10 — Maior Margem")
    top_margin = df.sort("margin_pct", descending=True).head(10).to_pandas()
    top_margin = top_margin[["full_name", "category", "margin_pct", "revenue"]].copy()
    top_margin.columns = ["Produto", "Categoria", "Margem (%)", "Receita (R$)"]
    top_margin["Margem (%)"]  = top_margin["Margem (%)"].apply(lambda x: f"{x:.1f}%")
    top_margin["Receita (R$)"] = top_margin["Receita (R$)"].apply(lambda x: f"R$ {x:,.2f}")
    st.dataframe(top_margin, use_container_width=True, hide_index=True)

with col2:
    st.subheader("⚠️ Bottom 10 — Menor Margem")
    bot_margin = df.sort("margin_pct").head(10).to_pandas()
    bot_margin = bot_margin[["full_name", "category", "margin_pct", "revenue"]].copy()
    bot_margin.columns = ["Produto", "Categoria", "Margem (%)", "Receita (R$)"]
    bot_margin["Margem (%)"]  = bot_margin["Margem (%)"].apply(lambda x: f"{x:.1f}%")
    bot_margin["Receita (R$)"] = bot_margin["Receita (R$)"].apply(lambda x: f"R$ {x:,.2f}")
    st.dataframe(bot_margin, use_container_width=True, hide_index=True)

