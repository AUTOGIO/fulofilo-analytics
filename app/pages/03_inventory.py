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
from app.db import get_conn, get_inventory_alerts, get_stock_turnover, get_data_mtime
from app.components.sidebar import render_sidebar, render_page_header
from app.components.hud import inject_hud_css, render_hud_topbar, alert_badge, hud_plotly_layout
from app.utils.inventory_ops import load_inventory, adjust_stock, sync_to_excel

st.set_page_config(page_title="Estoque — FulôFiló", page_icon=_FAVICON, layout="wide")
inject_hud_css()
render_sidebar()
render_page_header()
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
# ── Giro do Estoque (Stock Turnover) KPIs ─────────────────────────────────────
@st.cache_data
def load_turnover(data_version: str):  # noqa: ARG001
    return get_stock_turnover(get_conn())

giro_df = load_turnover(get_data_mtime())

if not giro_df.is_empty():
    giro_pd = giro_df.to_pandas()
    avg_giro  = giro_pd["giro"].mean()
    n_alto    = (giro_pd["giro_class"] == "🔥 Alto").sum()
    n_normal  = (giro_pd["giro_class"] == "✅ Normal").sum()
    n_baixo   = (giro_pd["giro_class"] == "🐢 Baixo").sum()
    n_zerado  = (giro_pd["giro_class"] == "⚠️ Sem estoque").sum()

    st.markdown("""
<div style="background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.20);
border-radius:10px;padding:12px 18px;margin-bottom:12px;">
<span style="font-size:0.7rem;letter-spacing:0.12em;color:#4A5568;text-transform:uppercase;">
🔄 Giro do Estoque — Vendas ÷ Estoque Atual
</span></div>
""", unsafe_allow_html=True)

    g1, g2, g3, g4, g5 = st.columns(5)
    g1.metric("📊 Giro Médio",     f"{avg_giro:.2f}x")
    g2.metric("🔥 Giro Alto",      f"{n_alto}",   delta="≥ 3×", delta_color="normal")
    g3.metric("✅ Giro Normal",    f"{n_normal}", delta="1–3×", delta_color="off")
    g4.metric("🐢 Giro Baixo",    f"{n_baixo}",  delta="< 1×", delta_color="inverse")
    g5.metric("⚠️ Sem Estoque",   f"{n_zerado}", delta_color="inverse")

    with st.expander("📋 Tabela completa de Giro por Produto", expanded=False):
        giro_show = giro_pd[["product","category","qty_sold","current_stock","giro","giro_class"]].copy()
        giro_show.columns = ["Produto","Categoria","Qtd Vendida","Estoque Atual","Giro (x)","Classe"]
        giro_show = giro_show.sort_values("Giro (x)", ascending=False)
        st.dataframe(giro_show, use_container_width=True, hide_index=True)

st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Níveis", "🔄 Reposição", "💰 Valor em Estoque"])

COLOR_MAP = {
    "🔴 Crítico": "#FF4455",
    "🟡 Baixo":   "#FFD700",
    "🟢 OK":      "#00FF88",
}

CATEGORY_COLORS = {
    "Camisetas Básicas":     "#00D4FF",
    "Baby Look":             "#FF79C6",
    "Regatas":               "#FFD700",
    "Camisetas Infantis":    "#A78BFA",
    "Canecas Ágata Pequena": "#00FF88",
    "Canecas Ágata Grande":  "#34D399",
    "Canecas Loucas":        "#FB923C",
    "Cangas":                "#F43F5E",
    "Chaveiros Femininos":   "#F472B6",
    "Chaveiros Masculinos":  "#60A5FA",
}

with tab1:
    all_cats = sorted(pdf["category"].unique().tolist())
    alert_filter = st.multiselect(
        "Filtrar Status", ["🔴 Crítico","🟡 Baixo","🟢 OK"],
        default=["🔴 Crítico","🟡 Baixo","🟢 OK"]
    )
    cat_filter = st.multiselect("Filtrar Categoria", all_cats, default=all_cats)
    view = pdf[pdf["alert"].isin(alert_filter)] if alert_filter else pdf
    if cat_filter:
        view = view[view["category"].isin(cat_filter)]
    fig = px.bar(
        view.sort_values(["category","current_stock"]),
        x="current_stock", y="product", color="category",
        color_discrete_map=CATEGORY_COLORS, orientation="h",
        labels={"current_stock":"Estoque Atual","product":"Produto","category":"Categoria"},
        title="Estoque Atual por Produto — por Categoria",
    )
    fig.update_traces(marker_line_width=0)
    hud_plotly_layout(fig, height=max(420, len(view)*22))
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
                build_report(output_path=out, selected_sheets={"Inventory"})
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
        # 'cost' is the parquet column name; alias to unit_cost for downstream join
        prod = pl.read_parquet(prod_path).select([pl.col("slug"), pl.col("cost").alias("unit_cost")])
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

# ── Stock Adjustment + Excel Sync ──────────────────────────────────────────────
st.divider()
st.subheader("🔧 Ajustar Estoque")

inv_full = load_inventory()
if not inv_full.is_empty():
    inv_pd_full = inv_full.to_pandas()

    adj_col1, adj_col2 = st.columns([3, 1])

    with adj_col1:
        with st.form("stock_adjust_form", clear_on_submit=False):
            fc1, fc2, fc3 = st.columns([3, 1, 1])
            with fc1:
                product_options = inv_pd_full["product"].tolist()
                selected_product = st.selectbox("Produto", product_options)
            with fc2:
                cur_stock_vals = inv_pd_full.loc[
                    inv_pd_full["product"] == selected_product, "current_stock"
                ].values
                slug_vals = inv_pd_full.loc[
                    inv_pd_full["product"] == selected_product, "slug"
                ].values
                cur_stock = int(cur_stock_vals[0]) if len(cur_stock_vals) else 0
                st.metric("Estoque Atual", cur_stock)
            with fc3:
                new_qty = st.number_input("Novo Estoque", min_value=0, value=cur_stock, step=1)

            submitted_adj = st.form_submit_button("💾 Salvar Ajuste", use_container_width=True)

        if submitted_adj and len(slug_vals):
            ok = adjust_stock(str(slug_vals[0]), int(new_qty))
            if ok:
                st.success(
                    f"✅ **{selected_product}**: {cur_stock} → **{int(new_qty)}** un. "
                    f"· Parquet e Excel sincronizados ✔"
                )
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("❌ Falha ao ajustar estoque.")

    with adj_col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        if st.button("🔄 Sync tudo → Excel", use_container_width=True, type="primary"):
            path = sync_to_excel()
            if path:
                st.success(f"✅ `{Path(path).name}` atualizado!")
            else:
                st.error("❌ Excel não encontrado.")

