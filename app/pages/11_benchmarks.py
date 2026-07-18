import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
_FAVICON = str(Path(__file__).resolve().parent.parent / "assets" / "favicon.png")
sys.path.insert(0, str(ROOT))
from app.db import get_conn, get_data_mtime
from app.components.sidebar import render_sidebar
from app.components.hud import inject_hud_css, hud_plotly_layout
from app.components.terminal import page_command_header, render_terminal_css
from core.benchmarking.segment_benchmarks import abc_benchmarks, category_benchmarks
from core.benchmarking.period_benchmarks import monthly_comparison
from core.benchmarking.channel_benchmarks import channel_benchmarks, weekday_vs_weekend

st.set_page_config(page_title="Benchmarks — FulôFiló", page_icon=_FAVICON, layout="wide")
inject_hud_css()
render_terminal_css()
render_sidebar()
page_command_header("Benchmarks", "BM / segments", "category, period, channel, and ABC self-benchmarks")

@st.cache_data
def load(data_version: str):
    conn = get_conn()
    try:
        return {
            "categories": category_benchmarks(conn),
            "abc": abc_benchmarks(conn),
            "months": monthly_comparison(conn),
            "channels": channel_benchmarks(conn),
            "daytype": weekday_vs_weekend(conn),
        }
    finally:
        conn.close()

data = load(get_data_mtime())

st.subheader("Categorias — receita e giro")
cat = data["categories"]
if not cat.is_empty():
    pdf = cat.to_pandas()
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(pdf, x="category", y="revenue", title="Receita por categoria")
        hud_plotly_layout(fig, height=360)
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig2 = px.bar(pdf, x="category", y="turnover", title="Giro por categoria")
        hud_plotly_layout(fig2, height=360)
        st.plotly_chart(fig2, width="stretch")

st.subheader("ABC — contribuição")
if not data["abc"].is_empty():
    st.dataframe(data["abc"], width="stretch", hide_index=True)

st.subheader("MoM — últimos meses")
if not data["months"].is_empty():
    st.dataframe(data["months"], width="stretch", hide_index=True)

st.subheader("Canal de pagamento")
if not data["channels"].is_empty():
    st.dataframe(data["channels"], width="stretch", hide_index=True)

st.subheader("Semana vs fim de semana (proxy turístico)")
if not data["daytype"].is_empty():
    st.dataframe(data["daytype"], width="stretch", hide_index=True)
