"""
FulôFiló — 📦 Gestão de Estoque (Enhanced)
============================================
Critical alert banner, reorder table with suggested qty, stacked value chart.
"""

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
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
    st.info("⚙️ Estoque não configurado. Preencha `data/raw/inventory_TEMPLATE.csv` e execute `etl/ingest_eleve.py`.")
    st.stop()

pdf = df.to_pandas()

# ── Critical items banner ──────────────────────────────────────────────────────
criticos = pdf[pdf["alert"] == "🔴 Crítico"]
if not criticos.empty:
    names = ", ".join(criticos["product"].tolist()[:5])
    extra = f" + {len(criticos)-5} mais" if len(criticos) > 5 else ""
    st.error(f"🚨 **{len(criticos)} ITEM(NS) CRÍTICO(S):** {names}{extra} — estoque abaixo do mínimo!")

# ── KPI cards ──────────────────────────────────────────────────────────────────
total   = len(pdf)
n_crit  = len(criticos)
n_baixo = len(pdf[pdf["alert"] == "🟡 Baixo"])
n_ok    = len(pdf[pdf["alert"] == "🟢 OK"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("📦 Total SKUs",  total)
c2.metric("🔴 Crítico",     n_crit,  delta=f"-{n_crit}" if n_crit > 0 else "0",   delta_color="inverse")
c3.metric("🟡 Baixo",       n_baixo, delta=f"-{n_baixo}" if n_baixo > 0 else "0", delta_color="inverse")
c4.metric("🟢 OK",          n_ok)
st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Níveis", "🔄 Reposição", "💰 Valor em Estoque"])

COLOR_MAP = {"🔴 Crítico": "#E74C3C", "🟡 Baixo": "#F2C94C", "🟢 OK": "#2D6A4F"}

with tab1:
    alert_filter = st.multiselect(
        "Filtrar Status", ["🔴 Crítico","🟡 Baixo","🟢 OK"],
        default=["🔴 Crítico","🟡 Baixo","🟢 OK"]
    )
    view = pdf[pdf["alert"].isin(alert_filter)] if alert_filter else pdf
    fig = px.bar(
        view.sort_values("current_stock"),
        x="current_stock", y="product", color="alert",
        color_discrete_map=COLOR_MAP, orientation="h",
        labels={"current_stock":"Estoque Atual","product":"Produto","alert":"Status"},
        title="Estoque Atual por Produto",
    )
    fig.update_layout(height=max(380, len(view)*22), showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("🔄 Itens abaixo do ponto de reposição")
    reorder = pdf[pdf["alert"].isin(["🔴 Crítico","🟡 Baixo"])].copy()
    if not reorder.empty:
        # Try to get max_stock / reorder_qty from inventory parquet
        import polars as pl
        inv_path = ROOT / "data" / "parquet" / "inventory.parquet"
        prod_path = ROOT / "data" / "parquet" / "products.parquet"
        if inv_path.exists() and prod_path.exists():
            inv = pl.read_parquet(inv_path).to_pandas()
            prod = pl.read_parquet(prod_path).select(["sku","suggested_price","unit_cost"]).to_pandas()
            merged = reorder.merge(inv[["product","reorder_qty"]], on="product", how="left")
            merged["Qtd Sugerida"] = merged["reorder_qty"].fillna(100).astype(int)
        else:
            merged = reorder.copy()
            merged["Qtd Sugerida"] = 100

        display = merged[["product","category","current_stock","min_stock","alert","Qtd Sugerida"]].copy()
        display.columns = ["Produto","Categoria","Estoque Atual","Mínimo","Status","Qtd Sugerida"]

        def row_style(row):
            bg = "background-color: #ffd6d6" if "Crítico" in str(row["Status"]) else "background-color: #fff3cd"
            return [bg]*len(row)

        st.dataframe(
            display.style.apply(row_style, axis=1),
            use_container_width=True, hide_index=True,
        )
        # Export button (calls Excel builder for Sheet 4 only)
        if st.button("📥 Exportar lista de reposição (Excel)"):
            from excel.build_report import build_report
            import tempfile, datetime
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / f"FuloFilo_Reposicao_{datetime.date.today()}.xlsx"
                build_report(output_path=out)
                st.download_button("⬇ Baixar Excel",
                                   data=out.read_bytes(), file_name=out.name,
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.success("✅ Todos os produtos estão com estoque adequado!")

with tab3:
    st.subheader("💰 Valor total em estoque por categoria")
    inv_path = ROOT / "data" / "parquet" / "inventory.parquet"
    prod_path = ROOT / "data" / "parquet" / "products.parquet"
    if inv_path.exists() and prod_path.exists():
        import polars as pl
        inv  = pl.read_parquet(inv_path)
        prod = pl.read_parquet(prod_path).select(["sku","unit_cost"])
        merged_pl = inv.join(prod, on="sku", how="left").with_columns(
            (pl.col("current_stock").cast(pl.Float64) * pl.col("unit_cost")).alias("value")
        )
        cat_val = (merged_pl.group_by("category")
                   .agg(pl.col("value").sum().alias("total_value"))
                   .sort("total_value", descending=True)
                   .to_pandas())
        fig3 = px.bar(cat_val, x="category", y="total_value",
                      title="Valor em Estoque por Categoria (R$)",
                      labels={"total_value":"Valor (R$)","category":"Categoria"},
                      color="total_value", color_continuous_scale="Greens")
        fig3.update_layout(height=380)
        st.plotly_chart(fig3, use_container_width=True)
        total_val = cat_val["total_value"].sum()
        st.metric("💰 Valor Total em Estoque", f"R$ {total_val:,.2f}")
    else:
        st.info("Dados de custo não disponíveis. Execute etl/build_catalog.py primeiro.")
