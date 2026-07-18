import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
_FAVICON = str(Path(__file__).resolve().parent.parent / "assets" / "favicon.png")
sys.path.insert(0, str(ROOT))
from app.db import get_conn, get_data_mtime
from app.components.sidebar import render_sidebar
from app.components.hud import inject_hud_css
from app.components.terminal import page_command_header, render_terminal_css
from core.simulation.scenarios import ScenarioParams, run_scenario

st.set_page_config(page_title="What-If — FulôFiló", page_icon=_FAVICON, layout="wide")
inject_hud_css()
render_terminal_css()
render_sidebar()
page_command_header("What-If", "SIM / scenarios", "stress-test demand, lead time, and coverage")

with st.sidebar:
    st.markdown("### Cenário")
    demand = st.slider("Multiplicador de demanda", 0.5, 2.0, 1.0, 0.05)
    lead_delta = st.slider("Δ lead time (dias)", -7, 21, 0)
    coverage = st.slider("Dias de cobertura", 15, 90, 45)
    cost_delta = st.slider("Δ custo unitário (%)", -20.0, 30.0, 0.0)
    exclude = st.multiselect("Excluir categorias", [])

@st.cache_data
def simulate(data_version: str, demand, lead_delta, coverage, cost_delta, exclude_tuple):
    conn = get_conn()
    try:
        params = ScenarioParams(
            demand_multiplier=demand,
            lead_time_days_delta=int(lead_delta),
            coverage_days=int(coverage),
            unit_cost_delta_pct=float(cost_delta),
            exclude_categories=list(exclude_tuple),
        )
        return run_scenario(conn, params)
    finally:
        conn.close()

result = simulate(get_data_mtime(), demand, lead_delta, coverage, cost_delta, tuple(exclude))
summary = result.get("summary", {})

c1, c2, c3, c4 = st.columns(4)
c1.metric("SKUs em risco (base)", summary.get("baseline_at_risk_skus", 0))
c2.metric("SKUs em risco (cenário)", summary.get("scenario_at_risk_skus", 0))
c3.metric("Δ risco", summary.get("delta_at_risk", 0))
c4.metric("Qtd sugerida (cenário)", summary.get("scenario_total_suggested_qty", 0))

scenario_df = result.get("scenario", pd.DataFrame())
if isinstance(scenario_df, pd.DataFrame) and not scenario_df.empty:
    show = scenario_df.nlargest(20, "projected_lost_profit_brl")[
        ["product", "category", "days_remaining", "suggested_qty", "projected_lost_profit_brl"]
    ]
    st.subheader("Top 20 SKUs em risco no cenário")
    st.dataframe(show, width="stretch", hide_index=True)
