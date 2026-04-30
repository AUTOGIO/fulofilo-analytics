"""
FulôFiló — Monthly Sales Block
================================
Renders month-filtered KPI totals + bar chart of revenue per month.
Reads the global month filter from session_state (set by sidebar).

Usage:
    from app.components.monthly_block import render_monthly_block
    render_monthly_block()
"""

import streamlit as st
import plotly.graph_objects as go
from app.db import get_monthly_breakdown, get_conn, get_data_mtime
from app.components.sidebar import get_month_filter
from app.components.hud import hud_plotly_layout, HUD

_MONTH_LABELS = {
    "2026-01": "Jan 2026", "2026-02": "Fev 2026", "2026-03": "Mar 2026",
    "2026-04": "Abr 2026", "2026-05": "Mai 2026", "2026-06": "Jun 2026",
    "2026-07": "Jul 2026", "2026-08": "Ago 2026", "2026-09": "Set 2026",
    "2026-10": "Out 2026", "2026-11": "Nov 2026", "2026-12": "Dez 2026",
}


def render_monthly_block(conn=None):
    if conn is None:
        conn = get_conn()

    # ── Load all monthly data (cached by parquet mtime) ───────────────────────
    @st.cache_data
    def _load_all(v):  # noqa: ARG001
        return get_monthly_breakdown(conn)

    df_all = _load_all(get_data_mtime())

    if df_all.is_empty():
        st.warning("Sem dados de vendas mensais disponíveis.")
        return

    months_raw = sorted(df_all["mes"].to_list())

    # ── Read global filter from session_state (set by sidebar) ────────────────
    selected = get_month_filter()  # list of 'YYYY-MM', empty = all

    # ── Apply filter ──────────────────────────────────────────────────────────
    if selected:
        df = df_all.filter(df_all["mes"].is_in(selected))
        label_parts = [_MONTH_LABELS.get(m, m) for m in sorted(selected)]
        subtitle = " · ".join(label_parts)
    else:
        df = df_all
        n = len(months_raw)
        subtitle = f"Acumulado · {n} {'mês' if n == 1 else 'meses'}"

    receita  = float(df["receita"].sum())
    unidades = float(df["unidades"].sum())
    ticket   = receita / unidades if unidades else 0.0

    # ── Section header ────────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.68rem;letter-spacing:0.15em;color:#4A5568;'
        'text-transform:uppercase;margin-bottom:10px;">◈ Vendas por Mês</div>',
        unsafe_allow_html=True,
    )

    # ── KPI summary cards ─────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Receita Total",  f"R$ {receita:,.2f}")
    c2.metric("📦 Unidades",       f"{int(unidades):,}")
    c3.metric("🎫 Ticket Médio",   f"R$ {ticket:,.2f}")

    # MoM delta on the 4th card (only meaningful with ≥2 months)
    rows_sorted = df.sort("mes").to_dicts()
    if len(rows_sorted) >= 2:
        prev_r = float(rows_sorted[-2]["receita"])
        last_r = float(rows_sorted[-1]["receita"])
        mom_pct = ((last_r - prev_r) / prev_r * 100) if prev_r else 0.0
        last_lbl = _MONTH_LABELS.get(rows_sorted[-1]["mes"], rows_sorted[-1]["mes"])
        c4.metric(
            f"📈 MoM ({last_lbl})",
            f"R$ {last_r:,.2f}",
            delta=f"{mom_pct:+.1f}%",
        )
    else:
        c4.metric("📅 Meses com dados", str(len(rows_sorted)))

    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

    # ── Bar chart — revenue per month (always shows all available months) ──────
    chart_df = df_all.sort("mes").to_dicts()
    if chart_df:
        labels   = [_MONTH_LABELS.get(r["mes"], r["mes"]) for r in chart_df]
        revenues = [float(r["receita"]) for r in chart_df]
        units    = [int(float(r["unidades"])) for r in chart_df]
        total_rev = sum(revenues)

        # Highlight selected bars vs dimmed
        selected_labels = set(
            _MONTH_LABELS.get(m, m) for m in (selected or months_raw)
        )
        bar_colors = [
            HUD["cyan"] if lbl in selected_labels else "rgba(0,212,255,0.25)"
            for lbl in labels
        ]

        fig = go.Figure()

        # Revenue bars
        fig.add_trace(go.Bar(
            name="Receita",
            x=labels,
            y=revenues,
            marker_color=bar_colors,
            marker_line_color="rgba(0,0,0,0)",
            text=[f"R$ {v:,.0f}" for v in revenues],
            textposition="outside",
            textfont=dict(color=HUD["text"], size=11),
            customdata=units,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Receita: R$ %{y:,.2f}<br>"
                "Unidades: %{customdata:,}<extra></extra>"
            ),
        ))

        # Total annotation line
        fig.add_hline(
            y=total_rev / len(revenues) if revenues else 0,
            line_dash="dot",
            line_color=HUD["gold"],
            annotation_text=f"Média R$ {total_rev / len(revenues):,.0f}",
            annotation_position="top right",
            annotation_font_color=HUD["gold"],
            annotation_font_size=11,
        )

        hud_plotly_layout(fig, height=280)
        fig.update_layout(
            margin=dict(l=10, r=10, t=36, b=10),
            xaxis_title="",
            yaxis_title="Receita (R$)",
            showlegend=False,
            title=dict(
                text=f"Receita por Mês  ·  <span style='color:{HUD['gold']};font-size:13px;'>"
                     f"Total R$ {total_rev:,.2f}</span>",
                font=dict(size=13, color=HUD["text"]),
                x=0,
            ),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Per-month table (always visible when >1 month) ────────────────────────
    if len(rows_sorted) > 1:
        with st.expander("📋 Detalhamento por mês", expanded=False):
            # Table header
            st.markdown(
                f'<table style="width:100%;border-collapse:collapse;font-size:0.82rem;">'
                f'<thead><tr style="color:{HUD["text_dim"]};text-transform:uppercase;'
                f'font-size:0.68rem;letter-spacing:0.08em;">'
                f'<th style="text-align:left;padding:6px 10px;">Mês</th>'
                f'<th style="text-align:right;padding:6px 10px;">Receita</th>'
                f'<th style="text-align:right;padding:6px 10px;">Unidades</th>'
                f'<th style="text-align:right;padding:6px 10px;">Ticket</th>'
                f'<th style="text-align:right;padding:6px 10px;">MoM</th>'
                f'</tr></thead><tbody>',
                unsafe_allow_html=True,
            )
            rows_html = ""
            prev_receita = None
            for r in rows_sorted:
                lbl   = _MONTH_LABELS.get(r["mes"], r["mes"])
                rev   = float(r["receita"])
                uni   = int(float(r["unidades"]))
                tkt   = rev / uni if uni else 0.0
                if prev_receita and prev_receita > 0:
                    mom   = (rev - prev_receita) / prev_receita * 100
                    mom_color = HUD["green"] if mom >= 0 else "#FF4455"
                    mom_str = f'<span style="color:{mom_color};">{mom:+.1f}%</span>'
                else:
                    mom_str = '<span style="color:#4A5568;">—</span>'
                rows_html += (
                    f'<tr style="border-top:1px solid rgba(0,212,255,0.08);">'
                    f'<td style="color:{HUD["text"]};padding:6px 10px;">{lbl}</td>'
                    f'<td style="color:{HUD["gold"]};text-align:right;padding:6px 10px;'
                    f'font-variant-numeric:tabular-nums;">R$ {rev:,.2f}</td>'
                    f'<td style="color:{HUD["text"]};text-align:right;padding:6px 10px;">{uni:,}</td>'
                    f'<td style="color:{HUD["text_dim"]};text-align:right;padding:6px 10px;">'
                    f'R$ {tkt:,.2f}</td>'
                    f'<td style="text-align:right;padding:6px 10px;">{mom_str}</td>'
                    f'</tr>'
                )
                prev_receita = rev

            # Total row
            total_uni = sum(int(float(r["unidades"])) for r in rows_sorted)
            total_tkt = receita / total_uni if total_uni else 0.0
            rows_html += (
                f'<tr style="border-top:2px solid {HUD["cyan"]};">'
                f'<td style="color:{HUD["cyan"]};font-weight:700;padding:8px 10px;">TOTAL</td>'
                f'<td style="color:{HUD["cyan"]};font-weight:700;text-align:right;padding:8px 10px;'
                f'font-variant-numeric:tabular-nums;">R$ {receita:,.2f}</td>'
                f'<td style="color:{HUD["cyan"]};font-weight:700;text-align:right;padding:8px 10px;">'
                f'{total_uni:,}</td>'
                f'<td style="color:{HUD["cyan"]};font-weight:700;text-align:right;padding:8px 10px;">'
                f'R$ {total_tkt:,.2f}</td>'
                f'<td></td>'
                f'</tr>'
            )
            st.markdown(rows_html + "</tbody></table>", unsafe_allow_html=True)

    st.markdown(
        f'<div style="font-size:0.7rem;color:#4A5568;text-align:right;margin-top:4px;">'
        f'{subtitle}</div>',
        unsafe_allow_html=True,
    )
