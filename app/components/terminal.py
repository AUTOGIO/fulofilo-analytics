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
    grid-template-columns: minmax(270px, 1.12fr) repeat(6, minmax(118px, 0.68fr));
    gap: 1px;
    background: #3A3A3A;
    border: 1px solid {HUD['border']};
    margin: 0 0 7px;
    box-shadow: 0 0 0 1px #000;
}}
.ff-terminal-brand,
.ff-terminal-cell {{
    background: linear-gradient(180deg, #191919 0%, #080808 100%);
    padding: 6px 8px;
    min-height: 52px;
}}
.ff-terminal-brand .kicker,
.ff-terminal-cell .label,
.ff-panel-title .meta,
.ff-status-label {{
    color: {HUD['text_dim']};
    font-size: 0.83rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}}
.ff-terminal-brand .kicker,
.ff-terminal-cell .label {{
    background: #C06E00;
    color: #060606;
    display: inline-block;
    font-weight: 900;
    line-height: 1;
    padding: 2px 5px;
}}
.ff-terminal-brand .name {{
    color: {HUD['text']};
    font-size: 1.25rem;
    font-weight: 800;
    letter-spacing: 0.01em;
    text-transform: uppercase;
    margin-top: 5px;
}}
.ff-terminal-brand .flow {{
    color: {HUD['gold']};
    font-size: 0.87rem;
    letter-spacing: 0;
    margin-top: 2px;
}}
.ff-terminal-cell .value {{
    color: {HUD['text']};
    font-size: 1.25rem;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
    margin-top: 5px;
}}
.ff-terminal-cell .sub {{
    color: {HUD['text_dim']};
    font-size: 0.86rem;
    margin-top: 1px;
}}
.ff-panel {{
    background: #050505;
    border: 1px solid {HUD['border']};
    border-radius: 0;
    margin-bottom: 7px;
    overflow: hidden;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
}}
.ff-panel-title {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 4px 7px;
    background: linear-gradient(90deg, #A90E24 0%, #7E0B1B 72%, #111 100%);
    border-bottom: 1px solid {HUD['border']};
}}
.ff-panel-title .title {{
    color: #F4EFE2;
    font-size: 0.95rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}}
.ff-panel-body {{
    padding: 6px;
}}
.ff-kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1px;
    background: #343434;
    border: 1px solid {HUD['border']};
}}
.ff-kpi {{
    --accent: {HUD['cyan']};
    background:
        linear-gradient(180deg, color-mix(in srgb, var(--accent) 30%, #090909), #060606 58%);
    border-top: 3px solid var(--accent);
    padding: 7px 8px;
    min-height: 66px;
}}
.ff-kpi .label {{
    color: #C8C0AC;
    font-size: 0.81rem;
    letter-spacing: 0.07em;
    text-transform: uppercase;
}}
.ff-kpi .value {{
    color: {HUD['text']};
    font-size: 1.3rem;
    font-weight: 850;
    font-variant-numeric: tabular-nums;
    margin-top: 5px;
}}
.ff-kpi .delta {{
    font-size: 0.85rem;
    margin-top: 1px;
}}
.ff-feed-row {{
    display: grid;
    grid-template-columns: 42px 62px minmax(0, 1fr);
    gap: 6px;
    padding: 4px 6px;
    border-bottom: 1px solid rgba(114,114,114,0.26);
    font-size: 0.93rem;
    background: #070707;
}}
.ff-feed-row:nth-child(even) {{ background: #101010; }}
.ff-feed-row:last-child {{ border-bottom: 0; }}
.ff-feed-time {{ color: {HUD['text_dim']}; font-variant-numeric: tabular-nums; }}
.ff-feed-type {{ font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }}
.ff-feed-msg {{ color: {HUD['gold']}; }}
.ff-status-grid {{
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 1px;
    background: #343434;
    border: 1px solid {HUD['border']};
    position: sticky;
    bottom: 0;
    z-index: 2;
}}
.ff-status-cell {{
    background: #060606;
    padding: 5px 8px;
}}
.ff-status-value {{
    color: {HUD['text']};
    font-size: 0.95rem;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
    margin-top: 2px;
}}
.ff-command-tape {{
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 1px;
    background: #383838;
    border: 1px solid {HUD['border']};
    margin: -1px 0 7px;
}}
.ff-command-tape span {{
    background: #0A0A0A;
    color: {HUD['gold']};
    display: block;
    font-size: 0.89rem;
    font-weight: 800;
    overflow: hidden;
    padding: 4px 7px;
    text-overflow: ellipsis;
    text-transform: uppercase;
    white-space: nowrap;
}}
.ff-command-tape span:nth-child(1),
.ff-command-tape span:nth-child(4) {{
    background: #C06E00;
    color: #060606;
}}
.ff-command-tape span:nth-child(2),
.ff-command-tape span:nth-child(5) {{
    background: #A90E24;
    color: #F4EFE2;
}}
.ff-command-tape span:nth-child(3),
.ff-command-tape span:nth-child(6) {{
    background: #063B7A;
    color: #EAF5FF;
}}
@media (max-width: 1200px) {{
    .ff-terminal-header {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .ff-kpi-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .ff-status-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .ff-command-tape {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
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
<div class="ff-kpi" style="--accent:{color};">
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


def command_tape(items: Iterable[str]) -> None:
    cells = "".join(f"<span>{_fmt(item)}</span>" for item in items)
    st.markdown(f'<div class="ff-command-tape">{cells}</div>', unsafe_allow_html=True)


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
    <div class="value" style="color:{HUD['gold']};font-size:1.03rem;">data/excel/FuloFilo_Master.xlsx</div>
    <div class="sub">generated parquet / DuckDB layers are read-only intelligence models</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    command_tape(
        [
            f"01) {section.split('/')[0].strip()} monitor",
            "02) Filters",
            "03) Analytics",
            "04) Watchlist",
            "05) Actions",
            f"06) {status}",
        ]
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
        return f'<div style="color:{HUD["text_dim"]};font-size:1.01rem;">No rows available.</div>'
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
