"""
FulôFiló — Análise ABC (Pareto)
================================
Classifies all products into A/B/C tiers based on cumulative revenue.
A = top 80% revenue | B = next 15% | C = bottom 5%
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.db import get_conn, get_abc_analysis

st.set_page_config(page_title="Análise ABC — FulôFiló", page_icon="📊", layout="wide")
st.title("📊 Análise ABC — Classificação Pareto")
st.markdown("Identifica quais produtos geram 80% da receita (Classe A), 15% (Classe B) e 5% (Classe C).")

@st.cache_data(ttl=300)
def load():
    conn = get_conn()
    return get_abc_analysis(conn)

df = load()

if df.is_empty():
    st.warning("Execute `etl/build_catalog.py` primeiro para gerar os dados.")
    st.stop()

pdf = df.to_pandas()
COLORS = {"A": "#2D6A4F", "B": "#F2C94C", "C": "#E74C3C"}

# ── Filters ──────────────────────────────────────────────────────────────────
col_f1, col_f2 = st.columns([2, 1])
with col_f1:
    categories = ["Todas"] + sorted(pdf["category"].unique().tolist())
    cat_filter = st.selectbox("Filtrar por Categoria", categories)
with col_f2:
    abc_filter = st.multiselect("Filtrar por Classe", ["A", "B", "C"], default=["A", "B", "C"])

filtered = pdf.copy()
if cat_filter != "Todas":
    filtered = filtered[filtered["category"] == cat_filter]
filtered = filtered[filtered["abc_class"].isin(abc_filter)]

st.divider()

# ── Pareto Bar Chart ──────────────────────────────────────────────────────────
st.subheader("Receita por Produto — Pareto")
fig = px.bar(
    filtered.sort_values("revenue", ascending=False),
    x="full_name", y="revenue",
    color="abc_class",
    color_discrete_map=COLORS,
    labels={"full_name": "Produto", "revenue": "Receita (R$)", "abc_class": "Classe ABC"},
    hover_data=["category", "qty_sold", "profit"],
)
fig.update_layout(xaxis_tickangle=-45, height=450, legend_title="Classe ABC")
st.plotly_chart(fig, width="stretch")

# ── Cumulative Curve ──────────────────────────────────────────────────────────
st.subheader("Curva Acumulada (Pareto)")
sorted_df = pdf.sort_values("revenue", ascending=False).reset_index(drop=True)
sorted_df["cum_pct"] = sorted_df["revenue"].cumsum() / sorted_df["revenue"].sum() * 100
sorted_df["rank"] = range(1, len(sorted_df) + 1)

fig2 = go.Figure()
fig2.add_trace(go.Bar(
    x=sorted_df["full_name"], y=sorted_df["revenue"],
    name="Receita", marker_color="#2D6A4F", opacity=0.7,
))
fig2.add_trace(go.Scatter(
    x=sorted_df["full_name"], y=sorted_df["cum_pct"],
    name="% Acumulado", yaxis="y2",
    line=dict(color="#F2C94C", width=3),
    mode="lines+markers",
))
fig2.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="80% (Classe A)")
fig2.update_layout(
    yaxis=dict(title="Receita (R$)"),
    yaxis2=dict(title="% Acumulado", overlaying="y", side="right", range=[0, 110]),
    xaxis_tickangle=-45, height=450,
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig2, width="stretch")

# ── Data Table ────────────────────────────────────────────────────────────────
st.subheader("📋 Tabela Completa")
display = filtered[["abc_class", "full_name", "category", "revenue", "qty_sold", "profit"]].copy()
display.columns = ["Classe", "Produto", "Categoria", "Receita (R$)", "Qtd Vendida", "Lucro (R$)"]
display["Receita (R$)"] = display["Receita (R$)"].apply(lambda x: f"R$ {x:,.2f}")
display["Lucro (R$)"] = display["Lucro (R$)"].apply(lambda x: f"R$ {x:,.2f}")
st.dataframe(display, width="stretch", hide_index=True)
