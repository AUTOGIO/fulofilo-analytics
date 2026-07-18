import sys
from pathlib import Path

import plotly.express as px
import polars as pl
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
_FAVICON = str(Path(__file__).resolve().parent.parent / "assets" / "favicon.png")
sys.path.insert(0, str(ROOT))
from app.db import get_conn, get_data_mtime
from app.components.sidebar import render_sidebar
from app.components.hud import inject_hud_css, hud_plotly_layout
from app.components.terminal import page_command_header, render_terminal_css
from core.cohorts.seasonal_cohorts import season_category_matrix
from core.cohorts.product_launch_cohorts import product_launch_cohorts
from core.forecasting.seasonal import load_tourist_config

st.set_page_config(page_title="Cohorts — FulôFiló", page_icon=_FAVICON, layout="wide")
inject_hud_css()
render_terminal_css()
render_sidebar()
page_command_header(
    "Cohorts",
    "CH / seasons",
    "tourist-season and product-launch cohorts (not customer retention)",
)

cfg = load_tourist_config()
st.caption(
    f"Alta temporada (meses {cfg.get('high_season_months', [])}) — "
    "clientes turísticos de compra única; cohorts por calendário e SKU."
)

@st.cache_data
def load(data_version: str):
    conn = get_conn()
    try:
        return season_category_matrix(conn), product_launch_cohorts(conn)
    finally:
        conn.close()

season_mat, launch = load(get_data_mtime())

st.subheader("Sazonalidade — mês × categoria")
if not season_mat.is_empty():
    pdf = season_mat.to_pandas()
    pivot = pdf.pivot_table(index="category", columns="month_num", values="units", aggfunc="sum").fillna(0)
    fig = px.imshow(pivot, aspect="auto", labels=dict(color="Unidades"))
    hud_plotly_layout(fig, height=440)
    st.plotly_chart(fig, width="stretch")

st.subheader("Lançamento de produto — meses desde 1ª venda")
if not launch.is_empty():
    top = launch.group_by("sku").agg(pl.col("revenue").sum().alias("total_rev")).sort("total_rev", descending=True).head(10)
    top_skus = top["sku"].to_list()
    sub = launch.filter(pl.col("sku").is_in(top_skus)).to_pandas()
    fig2 = px.line(sub, x="months_since_launch", y="units", color="sku", markers=True)
    hud_plotly_layout(fig2, height=400)
    st.plotly_chart(fig2, width="stretch")
else:
    st.info("Histórico insuficiente para curvas de lançamento.")
