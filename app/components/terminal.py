"""Institutional retail terminal widgets for the FulôFiló dashboard."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st

from app.components.hud import HUD


ROOT = Path(__file__).resolve().parent.parent.parent


def _fmt(value: object) -> str:
    return escape("" if value is None else str(value))


def money(value: float | int | None, digits: int = 0) -> str:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0.0
    return f"R$ {amount:,.{digits}f}"


def number(value: float | int | None, digits: int = 0) -> str:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0.0
    return f"{amount:,.{digits}f}"


def status_color(state: str) -> str:
    normalized = (state or "").lower()
    if normalized in {"ok", "ready", "online", "healthy", "synced"}:
        return HUD["green"]
    if normalized in {"warn", "warning", "incomplete", "bootstrap"}:
        return HUD["amber"]
    if normalized in {"risk", "critical", "error", "offline"}:
        return HUD["red"]
    return HUD["cyan"]


def render_terminal_css() -> None:
    st.markdown(f"""
<style>
.ff-terminal-header {{
    display: grid;
    grid-template-columns: minmax(250px, 1.15fr) repeat(6, minmax(120px, 0.7fr));
    gap: 1px;
    background: {HUD['border']};
    border: 1px solid {HUD['border']};
    margin: 0 0 10px;
}}
.ff-terminal-brand,
.ff-terminal-cell {{
    background: linear-gradient(180deg, rgba(13,24,23,0.98), rgba(6,10,11,0.98));
    padding: 8px 10px;
    min-height: 58px;
}}
.ff-terminal-brand .kicker,
.ff-terminal-cell .label,
.ff-panel-title .meta,
.ff-status-label {{
    color: {HUD['text_dim']};
    font-size: 0.62rem;
    letter-spacing: 0.13em;
    text-transform: uppercase;
}}
.ff-terminal-brand .name {{
    color: {HUD['text']};
    font-size: 1.05rem;
    font-weight: 800;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}}
.ff-terminal-brand .flow {{
    color: {HUD['gold']};
    font-size: 0.66rem;
    letter-spacing: 0.08em;
    margin-top: 3px;
}}
.ff-terminal-cell .value {{
    color: {HUD['text']};
    font-size: 1.02rem;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
    margin-top: 5px;
}}
.ff-terminal-cell .sub {{
    color: {HUD['text_dim']};
    font-size: 0.66rem;
    margin-top: 2px;
}}
.ff-panel {{
    background: linear-gradient(180deg, rgba(12,22,22,0.98), rgba(7,11,12,0.98));
    border: 1px solid {HUD['border']};
    border-radius: 4px;
    margin-bottom: 10px;
    overflow: hidden;
}}
.ff-panel-title {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 7px 9px;
    background: rgba(255,255,255,0.025);
    border-bottom: 1px solid {HUD['border']};
}}
.ff-panel-title .title {{
    color: {HUD['text']};
    font-size: 0.76rem;
    font-weight: 800;
    letter-spacing: 0.10em;
    text-transform: uppercase;
}}
.ff-panel-body {{
    padding: 9px;
}}
.ff-kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1px;
    background: {HUD['border']};
    border: 1px solid {HUD['border']};
}}
.ff-kpi {{
    background: #091010;
    padding: 9px;
    min-height: 72px;
}}
.ff-kpi .label {{
    color: {HUD['text_dim']};
    font-size: 0.60rem;
    letter-spacing: 0.13em;
    text-transform: uppercase;
}}
.ff-kpi .value {{
    color: {HUD['text']};
    font-size: 1.08rem;
    font-weight: 850;
    font-variant-numeric: tabular-nums;
    margin-top: 6px;
}}
.ff-kpi .delta {{
    font-size: 0.66rem;
    margin-top: 2px;
}}
.ff-feed-row {{
    display: grid;
    grid-template-columns: 42px 62px minmax(0, 1fr);
    gap: 7px;
    padding: 6px 0;
    border-bottom: 1px solid rgba(87,113,108,0.18);
    font-size: 0.72rem;
}}
.ff-feed-row:last-child {{ border-bottom: 0; }}
.ff-feed-time {{ color: {HUD['text_dim']}; font-variant-numeric: tabular-nums; }}
.ff-feed-type {{ font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }}
.ff-feed-msg {{ color: {HUD['text']}; }}
.ff-status-grid {{
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 1px;
    background: {HUD['border']};
    border: 1px solid {HUD['border']};
    position: sticky;
    bottom: 0;
    z-index: 2;
}}
.ff-status-cell {{
    background: #060A0B;
    padding: 7px 9px;
}}
.ff-status-value {{
    color: {HUD['text']};
    font-size: 0.75rem;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
    margin-top: 3px;
}}
@media (max-width: 1200px) {{
    .ff-terminal-header {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .ff-kpi-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .ff-status-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}
</style>
""", unsafe_allow_html=True)


def panel(title: str, meta: str = "", body: str = "") -> None:
    st.markdown(
        f"""
<section class="ff-panel">
  <div class="ff-panel-title">
    <span class="title">{_fmt(title)}</span>
    <span class="meta">{_fmt(meta)}</span>
  </div>
  <div class="ff-panel-body">{body}</div>
</section>
""",
        unsafe_allow_html=True,
    )


def kpi_grid(items: Iterable[dict[str, str]]) -> str:
    cells = []
    for item in items:
        color = item.get("color", HUD["cyan"])
        cells.append(
            f"""
<div class="ff-kpi">
  <div class="label">{_fmt(item.get('label'))}</div>
  <div class="value" style="color:{color};">{_fmt(item.get('value'))}</div>
  <div class="delta" style="color:{_fmt(item.get('delta_color', HUD['text_dim']))};">{_fmt(item.get('delta', ''))}</div>
</div>
"""
        )
    return f'<div class="ff-kpi-grid">{"".join(cells)}</div>'


def terminal_header(cells: Iterable[dict[str, str]]) -> None:
    parts = [
        """
<div class="ff-terminal-brand">
  <div class="kicker">FulôFiló AI</div>
  <div class="name">Retail Operations Terminal</div>
  <div class="flow">Excel master -> sync -> Parquet/DuckDB -> executive intelligence</div>
</div>
"""
    ]
    for cell in cells:
        color = cell.get("color", HUD["text"])
        parts.append(
            f"""
<div class="ff-terminal-cell">
  <div class="label">{_fmt(cell.get('label'))}</div>
  <div class="value" style="color:{color};">{_fmt(cell.get('value'))}</div>
  <div class="sub">{_fmt(cell.get('sub', ''))}</div>
</div>
"""
        )
    st.markdown(f'<div class="ff-terminal-header">{"".join(parts)}</div>', unsafe_allow_html=True)


def page_command_header(title: str, section: str, contract: str, status: str = "READ MODEL") -> None:
    st.markdown(
        f"""
<div class="ff-terminal-header" style="grid-template-columns:minmax(280px,1.2fr) minmax(170px,0.7fr) minmax(320px,1.4fr);">
  <div class="ff-terminal-brand">
    <div class="kicker">{_fmt(section)}</div>
    <div class="name">{_fmt(title)}</div>
    <div class="flow">{_fmt(contract)}</div>
  </div>
  <div class="ff-terminal-cell">
    <div class="label">Runtime State</div>
    <div class="value" style="color:{HUD['green']};">{_fmt(status)}</div>
    <div class="sub">Excel-first operational architecture</div>
  </div>
  <div class="ff-terminal-cell">
    <div class="label">Canonical Source</div>
    <div class="value" style="color:{HUD['gold']};font-size:0.78rem;">data/excel/FuloFilo_Master.xlsx</div>
    <div class="sub">generated parquet / DuckDB layers are read-only intelligence models</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def feed(rows: Iterable[dict[str, str]]) -> str:
    html_rows = []
    for row in rows:
        color = row.get("color", HUD["cyan"])
        html_rows.append(
            f"""
<div class="ff-feed-row">
  <div class="ff-feed-time">{_fmt(row.get('time'))}</div>
  <div class="ff-feed-type" style="color:{color};">{_fmt(row.get('type'))}</div>
  <div class="ff-feed-msg">{_fmt(row.get('message'))}</div>
</div>
"""
        )
    return "".join(html_rows)


def dataframe_table(df: pd.DataFrame, max_rows: int = 8) -> str:
    if df.empty:
        return f'<div style="color:{HUD["text_dim"]};font-size:0.76rem;">No rows available.</div>'
    return df.head(max_rows).to_html(index=False, escape=True)


def status_bar(cells: Iterable[dict[str, str]]) -> None:
    html_cells = []
    for cell in cells:
        state = cell.get("state", "")
        color = cell.get("color", status_color(state))
        html_cells.append(
            f"""
<div class="ff-status-cell">
  <div class="ff-status-label">{_fmt(cell.get('label'))}</div>
  <div class="ff-status-value" style="color:{color};">{_fmt(cell.get('value'))}</div>
</div>
"""
        )
    st.markdown(f'<div class="ff-status-grid">{"".join(html_cells)}</div>', unsafe_allow_html=True)
