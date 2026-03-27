"""
FulôFiló — Gestão de Estoque
==============================
Inventory alerts, stock levels, and reorder recommendations.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.db import get_conn, get_inventory_alerts

st.set_page_config(page_title="Estoque — FulôFiló", page_icon="📦", layout="wide")
st.title("📦 Gestão de Estoque")
st.markdown("Monitore níveis de estoque, alertas de reposição e giro de produtos.")

@st.cache_data(ttl=60)
def load():
    conn = get_conn()
    return get_inventory_alerts(conn)

df = load()

if df.is_empty():
    st.info("⚙️ Estoque não configurado ainda.")
    st.markdown("""
    ### Como configurar o estoque:
    1. Abra o arquivo `data/raw/inventory_TEMPLATE.csv`
    2. Preencha a coluna `current_stock` com as contagens reais de cada produto
    3. Execute: `uv run python etl/ingest_eleve.py`
    4. Recarregue esta página
    """)
    st.stop()

pdf = df.to_pandas()

# ── KPI Cards ─────────────────────────────────────────────────────────────────
total = len(pdf)
critico = len(pdf[pdf["alert"] == "🔴 Crítico"])
baixo = len(pdf[pdf["alert"] == "🟡 Baixo"])
ok = len(pdf[pdf["alert"] == "🟢 OK"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("📦 Total Produtos", total)
c2.metric("🔴 Crítico", critico, delta=f"-{critico}" if critico > 0 else None, delta_color="inverse")
c3.metric("🟡 Baixo", baixo, delta=f"-{baixo}" if baixo > 0 else None, delta_color="inverse")
c4.metric("🟢 OK", ok)

st.divider()

# ── Alert Filter ──────────────────────────────────────────────────────────────
alert_filter = st.multiselect(
    "Filtrar por Status",
    ["🔴 Crítico", "🟡 Baixo", "🟢 OK"],
    default=["🔴 Crítico", "🟡 Baixo"],
)
filtered = pdf[pdf["alert"].isin(alert_filter)] if alert_filter else pdf

# ── Stock Level Bar Chart ─────────────────────────────────────────────────────
st.subheader("📊 Nível de Estoque por Produto")
color_map = {"🔴 Crítico": "#E74C3C", "🟡 Baixo": "#F2C94C", "🟢 OK": "#2D6A4F"}
fig = px.bar(
    filtered.sort_values("current_stock"),
    x="current_stock",
    y="product",
    color="alert",
    color_discrete_map=color_map,
    orientation="h",
    labels={"current_stock": "Estoque Atual", "product": "Produto", "alert": "Status"},
    title="Estoque Atual vs. Mínimo",
)
# Add minimum stock line
for _, row in filtered.iterrows():
    fig.add_shape(
        type="line",
        x0=row["min_stock"], x1=row["min_stock"],
        y0=row["product"], y1=row["product"],
        line=dict(color="black", width=2, dash="dot"),
    )
fig.update_layout(height=max(400, len(filtered) * 25), showlegend=True)
st.plotly_chart(fig, width="stretch")

# ── Reorder Recommendations ───────────────────────────────────────────────────
st.subheader("🔄 Recomendações de Reposição")
reorder = filtered[filtered["alert"].isin(["🔴 Crítico", "🟡 Baixo"])].copy()
if not reorder.empty:
    reorder.columns = ["Produto", "Categoria", "Estoque Atual", "Estoque Mínimo", "Status"]
    st.dataframe(
        reorder.style.map(
            lambda v: "background-color: #ffd6d6" if "Crítico" in str(v) else
                      "background-color: #fff3cd" if "Baixo" in str(v) else "",
            subset=["Status"]
        ),
        width="stretch",
        hide_index=True,
    )
else:
    st.success("✅ Todos os produtos estão com estoque adequado!")
