import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
_FAVICON = str(Path(__file__).resolve().parent.parent / "assets" / "favicon.png")
sys.path.insert(0, str(ROOT))
from app.db import get_conn, get_data_mtime
from app.components.sidebar import render_sidebar
from app.components.hud import inject_hud_css, hud_plotly_layout
from app.components.terminal import page_command_header, render_terminal_css
from core.forecasting.runner import run_forecasts
from core.forecasting.seasonal import compute_season_index

st.set_page_config(page_title="Forecasting — FulôFiló", page_icon=_FAVICON, layout="wide")
inject_hud_css()
render_terminal_css()
render_sidebar()
page_command_header("Forecasting", "FC / demand", "category + Class A SKU projections with seasonal overlay")

@st.cache_data
def load(data_version: str):
    conn = get_conn()
    try:
        forecasts = run_forecasts(conn)
        season = compute_season_index(conn)
    finally:
        conn.close()
    return forecasts, season

forecasts, season = load(get_data_mtime())
cat_df = pd.DataFrame(forecasts.get("category_forecasts", []))
sku_df = pd.DataFrame(forecasts.get("sku_forecasts", []))

if cat_df.empty:
    st.warning("Sem dados de vendas para previsão. Execute `bash scripts/sync_excel.sh`.")
    st.stop()

st.subheader("Previsão por categoria (7 dias)")
show = cat_df.sort_values("forecast_units", ascending=False)
st.dataframe(show, width="stretch", hide_index=True)

if {"forecast_units", "lower_bound", "upper_bound", "entity"}.issubset(show.columns):
    fig = px.bar(show.head(15), x="entity", y="forecast_units", error_y=show.head(15)["upper_bound"] - show.head(15)["forecast_units"])
    hud_plotly_layout(fig, height=400)
    st.plotly_chart(fig, width="stretch")

st.subheader("Índice sazonal (mês × categoria)")
if not season.is_empty():
    heat = season.to_pandas()
    pivot = heat.pivot_table(index="category", columns="month_num", values="season_index", aggfunc="mean").fillna(0)
    fig2 = px.imshow(pivot, aspect="auto", labels=dict(color="Índice"))
    hud_plotly_layout(fig2, height=420)
    st.plotly_chart(fig2, width="stretch")

st.subheader("Class A — previsão SKU (30 dias)")
if not sku_df.empty:
    st.dataframe(sku_df.sort_values("forecast_units", ascending=False).head(30), width="stretch", hide_index=True)
else:
    st.caption("Nenhum SKU Classe A com histórico suficiente.")
