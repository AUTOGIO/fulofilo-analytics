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
from app.components.sidebar import render_sidebar, render_page_header, get_selected_period
from app.components.hud import inject_hud_css, render_hud_topbar, hud_plotly_layout
from core.classification import classify_dataframe, FIXED_MARGIN_THRESHOLD, FIXED_QTY_THRESHOLD
from core.recommendations import enrich_with_recommendations
from core.reporting import generate_weekly_report
from core.alerts import generate_alerts
from core.analytics import aggregate_by_category

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
def load(data_version: str, period: str):  # noqa: ARG001
    conn = get_conn()
    return get_margin_matrix(conn, period=period)

df = load(get_data_mtime(), get_selected_period())

if df.is_empty():
    st.warning("Execute `etl/build_catalog.py` primeiro.")
    st.stop()

pdf = df.to_pandas()

# ── Intelligence layer — classify + enrich (once, before any filtering) ───────
@st.cache_data
def enrich_data(data_version: str, period: str):  # noqa: ARG001
    """Classify + add recommended actions. Cached per data version + period."""
    import polars as pl
    conn = get_conn()
    raw  = get_margin_matrix(conn, period=period).to_pandas()
    classified = classify_dataframe(raw)
    enriched   = enrich_with_recommendations(classified, display=True)
    return enriched

enriched_pdf = enrich_data(get_data_mtime(), get_selected_period())

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

# Quadrant lines — fixed business thresholds (deterministic, filter-stable)
# Change FIXED_MARGIN_THRESHOLD / FIXED_QTY_THRESHOLD in core/classification.py
fig.add_vline(
    x=FIXED_QTY_THRESHOLD,
    line_dash="dash", line_color="rgba(0,212,255,0.35)", line_width=1,
    annotation_text=f"Vol={int(FIXED_QTY_THRESHOLD)} un",
    annotation_font_color="rgba(0,212,255,0.6)",
    annotation_position="top right",
)
fig.add_hline(
    y=FIXED_MARGIN_THRESHOLD,
    line_dash="dash", line_color="rgba(0,212,255,0.35)", line_width=1,
    annotation_text=f"Margem={FIXED_MARGIN_THRESHOLD:.0f}%",
    annotation_font_color="rgba(0,212,255,0.6)",
    annotation_position="bottom right",
)

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

# ══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE LAYER — Classification + Recommendations + Alerts + Report
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("🧠 Inteligência Estratégica")

# ── Classification distribution KPIs ─────────────────────────────────────────
dist = enriched_pdf["classification"].value_counts().to_dict()
k1, k2, k3, k4 = st.columns(4)
k1.metric("🌟 Stars",       dist.get("Star",       0))
k2.metric("🐄 Cash Cows",   dist.get("Cash Cow",   0))
k3.metric("💎 Hidden Gems", dist.get("Hidden Gem", 0))
k4.metric("🐕 Dogs",        dist.get("Dog",        0))

# ── Enriched product table (filterable by current category selection) ─────────
st.markdown("#### Classificação + Recomendação por Produto")
display_enriched = enriched_pdf.copy()
if cat_filter != "Todas":
    display_enriched = display_enriched[display_enriched["category"] == cat_filter]

show_cols = [c for c in ["full_name", "category", "qty_sold", "margin_pct",
                          "revenue", "classification", "recommended_action"]
             if c in display_enriched.columns]
show_enriched = display_enriched[show_cols].copy()
show_enriched = show_enriched.rename(columns={
    "full_name": "Produto", "category": "Categoria", "qty_sold": "Qtd Vendida",
    "margin_pct": "Margem", "revenue": "Receita (R$)",
    "classification": "Classificação", "recommended_action": "Ação Recomendada",
})
if "Margem" in show_enriched.columns:
    show_enriched["Margem"] = show_enriched["Margem"].apply(lambda x: f"{x*100:.1f}%")
if "Receita (R$)" in show_enriched.columns:
    show_enriched["Receita (R$)"] = show_enriched["Receita (R$)"].apply(lambda x: f"R$ {x:,.2f}")

st.dataframe(show_enriched, use_container_width=True, hide_index=True)

# ── Alerts panel ─────────────────────────────────────────────────────────────
st.divider()
st.markdown("#### ⚡ Alertas Operacionais")

@st.cache_data
def load_alerts(data_version: str):  # noqa: ARG001
    import polars as pl
    inv_path = Path(__file__).resolve().parent.parent.parent / "data" / "parquet" / "inventory.parquet"
    inv_df   = pl.read_parquet(str(inv_path)).to_pandas() if inv_path.exists() else None
    return generate_alerts(enriched_pdf, inventory_df=inv_df)

alert_result = load_alerts(get_data_mtime())
alerts       = alert_result.get("alerts", [])
skipped      = alert_result.get("skipped_rules", [])
summary      = alert_result.get("summary", {})

if alerts:
    for a in alerts:
        icon = "🔴" if a["severity"] == "high" else "🟡"
        st.warning(f"{icon} {a['message']}")
else:
    st.success("✅ Nenhum alerta ativo no momento.")

if skipped:
    with st.expander(f"ℹ️ Regras ignoradas ({len(skipped)})", expanded=False):
        for s in skipped:
            st.caption(f"**{s['rule']}**: {s['reason']}")

# ── Category analytics ────────────────────────────────────────────────────────
st.divider()
st.markdown("#### 📊 Resumo por Categoria")
cat_summary = aggregate_by_category(enriched_pdf)
if not cat_summary.empty:
    cat_show = cat_summary.copy()
    cat_show["avg_margin_pct"] = cat_show["avg_margin_pct"].apply(lambda x: f"{x*100:.1f}%")
    cat_show["total_revenue"]  = cat_show["total_revenue"].apply(lambda x: f"R$ {x:,.2f}")
    rename_cat = {
        "category": "Categoria", "avg_margin_pct": "Margem Média",
        "total_revenue": "Receita Total", "total_qty_sold": "Qtd Total",
        "product_count": "Produtos",
    }
    if "star_count" in cat_show.columns: rename_cat["star_count"] = "⭐ Stars"
    if "dog_count"  in cat_show.columns: rename_cat["dog_count"]  = "🐕 Dogs"
    cat_show = cat_show.rename(columns=rename_cat)
    st.dataframe(cat_show, use_container_width=True, hide_index=True)

# ── Weekly report generation ──────────────────────────────────────────────────
st.divider()
st.markdown("#### 📄 Relatório Semanal")
col_r1, col_r2 = st.columns([3, 1])
with col_r1:
    st.caption("Gera JSON + Markdown em `data/outputs/weekly_report.json`")
with col_r2:
    if st.button("📥 Gerar Relatório", use_container_width=True):
        with st.spinner("Gerando..."):
            report = generate_weekly_report(enriched_pdf)
        meta = report.get("metadata", {})
        st.success(
            f"✅ Relatório gerado — {meta.get('total_products', 0)} produtos, "
            f"distribuição: {meta.get('distribution', {})}"
        )
        conc = report.get("revenue_concentration", {})
        if conc and "n_products" in conc:
            st.info(
                f"📊 Concentração de receita: **{conc['n_products']} produtos** "
                f"representam 80% da receita total "
                f"({conc.get('pct_of_catalog', 0)*100:.1f}% do catálogo)"
            )

