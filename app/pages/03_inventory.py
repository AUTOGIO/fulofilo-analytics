from pathlib import Path as _Path
_FAVICON = str(_Path(__file__).resolve().parent.parent / 'assets' / 'favicon.png')
"""
FulôFiló — 📦 Gestão de Estoque (HUD Edition)
===============================================
Critical alert banner, reorder table with HUD alert pills, stacked value chart.
"""

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from app.db import get_conn, get_inventory_alerts, get_data_mtime
from app.components.sidebar import render_sidebar
from app.components.hud import inject_hud_css, render_hud_topbar, alert_badge, hud_plotly_layout

st.set_page_config(page_title="Estoque — FulôFiló", page_icon=_FAVICON, layout="wide")
inject_hud_css()
render_sidebar()
render_hud_topbar("Gestão de Estoque", "📦")

st.markdown("Monitore níveis de estoque, alertas de reposição e giro de produtos.")

@st.cache_data
def load(data_version: str):  # noqa: ARG001
    conn = get_conn()
    return get_inventory_alerts(conn)

df = load(get_data_mtime())

if df.is_empty():
    st.info("⚙️ Estoque não configurado. Preencha `data/raw/inventory_TEMPLATE.csv` e execute `etl/ingest_eleve.py`.")
    st.stop()

pdf = df.to_pandas()

# ── Critical items banner ──────────────────────────────────────────────────────
criticos = pdf[pdf["alert"] == "🔴 Crítico"]
if not criticos.empty:
    names = ", ".join(criticos["product"].tolist()[:5])
    extra = f" + {len(criticos)-5} mais" if len(criticos) > 5 else ""
    st.markdown(f"""
<div style="
    background: rgba(255,68,85,0.10);
    border: 1px solid #FF4455;
    border-radius: 10px;
    padding: 12px 18px;
    margin-bottom: 16px;
    box-shadow: 0 0 16px rgba(255,68,85,0.25);
    font-size: 0.9rem;
    color: #FF4455;
">
🚨 <strong>{len(criticos)} ITEM(NS) CRÍTICO(S):</strong> {names}{extra} — estoque abaixo do mínimo!
</div>
""", unsafe_allow_html=True)

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

COLOR_MAP = {
    "🔴 Crítico": "#FF4455",
    "🟡 Baixo":   "#FFD700",
    "🟢 OK":      "#00FF88",
}

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
    fig.update_traces(marker_line_width=0)
    hud_plotly_layout(fig, height=max(380, len(view)*22))
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("🔄 Itens abaixo do ponto de reposição")
    reorder = pdf[pdf["alert"].isin(["🔴 Crítico","🟡 Baixo"])].copy()
    if not reorder.empty:
        import polars as pl
        inv_path  = ROOT / "data" / "parquet" / "inventory.parquet"
        prod_path = ROOT / "data" / "parquet" / "products.parquet"
        if inv_path.exists() and prod_path.exists():
            inv  = pl.read_parquet(inv_path).to_pandas()
            merged = reorder.merge(inv[["product","reorder_qty"]], on="product", how="left")
            merged["Qtd Sugerida"] = merged["reorder_qty"].fillna(100).astype(int)
        else:
            merged = reorder.copy()
            merged["Qtd Sugerida"] = 100

        display = merged[["product","category","current_stock","min_stock","alert","Qtd Sugerida"]].copy()
        display["alert"] = display["alert"].apply(lambda a: alert_badge(a))
        display.columns = ["Produto","Categoria","Estoque Atual","Mínimo","Status","Qtd Sugerida"]
        st.markdown(display.to_html(escape=False, index=False), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📥 Exportar lista de reposição (Excel)"):
            from excel.build_report import build_report
            import tempfile, datetime
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / f"FuloFilo_Reposicao_{datetime.date.today()}.xlsx"
                build_report(output_path=out)
                st.download_button(
                    "⬇ Baixar Excel", data=out.read_bytes(), file_name=out.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
    else:
        st.success("✅ Todos os produtos estão com estoque adequado!")

with tab3:
    st.subheader("💰 Valor total em estoque por categoria")
    inv_path  = ROOT / "data" / "parquet" / "inventory.parquet"
    prod_path = ROOT / "data" / "parquet" / "products.parquet"
    if inv_path.exists() and prod_path.exists():
        import polars as pl
        inv  = pl.read_parquet(inv_path)
        prod = pl.read_parquet(prod_path).select(["slug","cost","qty_sold"]).with_columns(
            (pl.col("cost") / pl.col("qty_sold").cast(pl.Float64)).alias("unit_cost")
        ).select(["slug","unit_cost"])
        merged_pl = inv.join(prod, left_on="slug", right_on="slug", how="left").with_columns(
            (pl.col("current_stock").cast(pl.Float64) * pl.col("unit_cost").fill_null(0.0)).alias("value")
        )
        cat_val = (merged_pl.group_by("category")
                   .agg(pl.col("value").sum().alias("total_value"))
                   .sort("total_value", descending=True)
                   .to_pandas())
        fig3 = px.bar(
            cat_val, x="category", y="total_value",
            title="Valor em Estoque por Categoria (R$)",
            labels={"total_value":"Valor (R$)","category":"Categoria"},
            color="total_value",
            color_continuous_scale=[[0, "#00FF88"], [1, "#00D4FF"]],
        )
        fig3.update_traces(marker_line_width=0)
        hud_plotly_layout(fig3, height=400)
        st.plotly_chart(fig3, use_container_width=True)
        total_val = cat_val["total_value"].sum()
        st.metric("💰 Valor Total em Estoque", f"R$ {total_val:,.2f}")
    else:
        st.info("Dados de custo não disponíveis. Execute etl/build_catalog.py primeiro.")
