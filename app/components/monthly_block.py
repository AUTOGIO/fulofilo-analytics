"""
FulôFiló — Monthly Sales Block
================================
Renders a month selector + KPI totals card, consistent with the HUD theme.
Usage:
    from app.components.monthly_block import render_monthly_block
    render_monthly_block(conn)
"""

import streamlit as st
from app.db import get_monthly_breakdown, get_conn, get_data_mtime

_MONTH_LABELS = {
    "2026-03": "Março 2026",
    "2026-04": "Abril 2026",
}


def render_monthly_block(conn=None):
    if conn is None:
        conn = get_conn()

    @st.cache_data
    def _load(v):  # noqa: ARG001
        return get_monthly_breakdown(conn)

    df = _load(get_data_mtime())

    if df.is_empty():
        st.warning("Sem dados de vendas mensais disponíveis.")
        return

    # Build month options from actual data
    months_raw = df["mes"].to_list()
    month_options = ["Todos os meses"] + [
        _MONTH_LABELS.get(m, m) for m in months_raw
    ]
    raw_map = {_MONTH_LABELS.get(m, m): m for m in months_raw}

    st.markdown(
        """
        <div style="
            border: 1px solid rgba(0,212,255,0.25);
            border-radius: 12px;
            padding: 18px 20px 14px;
            background: rgba(10,14,28,0.7);
            margin-bottom: 16px;
        ">
        <div style="
            font-size:0.68rem;
            letter-spacing:0.15em;
            color:#4A5568;
            text-transform:uppercase;
            margin-bottom:12px;
        ">◈ Vendas por Mês</div>
        """,
        unsafe_allow_html=True,
    )

    selected_label = st.selectbox(
        "Mês",
        month_options,
        label_visibility="collapsed",
        key="monthly_block_selector",
    )

    if selected_label == "Todos os meses":
        receita   = df["receita"].sum()
        unidades  = df["unidades"].sum()
        n_months  = len(months_raw)
        subtitle  = f"Acumulado · {n_months} {'mês' if n_months == 1 else 'meses'}"
    else:
        mes_raw = raw_map[selected_label]
        row = df.filter(df["mes"] == mes_raw)
        receita   = row["receita"].sum()
        unidades  = row["unidades"].sum()
        subtitle  = selected_label

    ticket = receita / unidades if unidades else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Receita",      f"R$ {receita:,.2f}")
    c2.metric("📦 Unidades",     f"{int(unidades):,}")
    c3.metric("🎫 Ticket Médio", f"R$ {ticket:,.2f}")

    st.markdown(
        f'<div style="font-size:0.7rem;color:#4A5568;text-align:right;'
        f'margin-top:4px;">{subtitle}</div></div>',
        unsafe_allow_html=True,
    )
