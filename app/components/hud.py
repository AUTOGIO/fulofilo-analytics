"""
FulôFiló — Shared HUD Component
================================
Central design system for the Premium HUD aesthetic.
Import and use on every page for consistent look & feel.

Usage:
    from app.components.hud import inject_hud_css, render_hud_topbar, abc_badge, alert_badge
"""

from datetime import datetime
import streamlit as st


# ── Palette ───────────────────────────────────────────────────────────────────
HUD = {
    "bg":          "#030303",
    "sidebar_bg":  "#080808",
    "surface":     "rgba(12,12,12,0.98)",
    "surface_hover": "rgba(26,26,24,0.98)",
    "cyan":        "#4BB7FF",
    "green":       "#13A84A",
    "gold":        "#F5A623",
    "red":         "#C21D38",
    "amber":       "#FF9F1A",
    "navy":        "#063B7A",
    "graphite":    "#111111",
    "muted":       "#686868",
    "text":        "#E7E3D7",
    "text_dim":    "#9B9588",
    "border":      "rgba(114,114,114,0.48)",
    "glow":        "0 0 0 rgba(0,0,0,0)",
    "glow_green":  "0 0 0 rgba(0,0,0,0)",
    "glow_red":    "0 0 0 rgba(0,0,0,0)",
}

# ABC class → (bg, text, glow)
ABC_STYLE = {
    "A": (HUD["green"],  "#080C18", HUD["glow_green"]),
    "B": (HUD["gold"],   "#080C18", "0 0 14px rgba(255,215,0,0.35)"),
    "C": (HUD["red"],    "#fff",    HUD["glow_red"]),
}

# Inventory alert → (bg, text, glow)
ALERT_STYLE = {
    "Crítico": (HUD["red"],   "#fff",    HUD["glow_red"]),
    "Baixo":   (HUD["gold"],  "#080C18", "0 0 14px rgba(255,215,0,0.35)"),
    "OK":      (HUD["green"], "#080C18", HUD["glow_green"]),
}

# Action tag (ABC decision) → (bg, text, glow)
ACTION_TAG_STYLE: dict[str, tuple[str, str, str]] = {
    "SCALE":    (HUD["green"], "#080C18", HUD["glow_green"]),
    "OPTIMIZE": (HUD["gold"],  "#080C18", "0 0 14px rgba(255,215,0,0.35)"),
    "REDUCE":   (HUD["red"],   "#fff",    HUD["glow_red"]),
}

# Priority level → (bg, text, glow)
PRIORITY_STYLE: dict[str, tuple[str, str, str]] = {
    "HIGH":   (HUD["red"],   "#fff",        HUD["glow_red"]),
    "MEDIUM": (HUD["gold"],  "#080C18",     "0 0 14px rgba(255,215,0,0.35)"),
    "LOW":    (HUD["muted"], HUD["text"],   "none"),
}

# Category confidence → (bg, text)
CONF_STYLE = {
    "high":      (HUD["green"], "#080C18"),
    "medium":    (HUD["gold"],  "#080C18"),
    "low":       (HUD["red"],   "#fff"),
    "unmatched": ("#2D3748",    HUD["text_dim"]),
    "manual":    (HUD["cyan"],  "#080C18"),
}


def inject_hud_css() -> None:
    """
    Inject global HUD CSS into the Streamlit page.
    Call once per page — ideally right after st.set_page_config().
    """
    st.markdown(f"""
<style>
/* ── Base ──────────────────────────────────────────────────────────────── */
html, body, [data-testid="stApp"] {{
    background:
        repeating-linear-gradient(0deg, rgba(255,159,26,0.030) 0, rgba(255,159,26,0.030) 1px, transparent 1px, transparent 26px),
        repeating-linear-gradient(90deg, rgba(255,255,255,0.018) 0, rgba(255,255,255,0.018) 1px, transparent 1px, transparent 72px),
        {HUD['bg']} !important;
    color: {HUD['text']};
    font-family: 'IBM Plex Mono', 'SF Mono', 'Menlo', 'Monaco', monospace;
}}
.block-container {{
    max-width: 1920px !important;
    padding: 0.35rem 0.65rem 2.25rem !important;
}}

/* ── Sidebar ───────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #121212 0%, #050505 100%) !important;
    border-right: 1px solid {HUD['border']} !important;
    box-shadow: none !important;
}}
[data-testid="stSidebar"] * {{ color: {HUD['text']} !important; }}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown span {{
    color: {HUD['text_dim']} !important;
}}
[data-testid="stSidebar"] hr {{
    border-color: {HUD['border']} !important;
    opacity: 1 !important;
}}
[data-testid="stSidebar"] a:hover {{
    color: {HUD['cyan']} !important;
    text-shadow: {HUD['glow']};
}}

/* ── KPI / Metric cards ────────────────────────────────────────────────── */
div[data-testid="metric-container"] {{
    background: linear-gradient(180deg, #151515, #070707) !important;
    border: 1px solid {HUD['border']} !important;
    border-radius: 4px !important;
    padding: 0.72rem 0.82rem !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03) !important;
}}
div[data-testid="stMetric"] {{
    background: linear-gradient(180deg, #151515, #070707) !important;
    border: 1px solid {HUD['border']} !important;
    border-radius: 0 !important;
    padding: 0.52rem 0.62rem !important;
}}
div[data-testid="metric-container"] [data-testid="stMetricLabel"] {{
    color: {HUD['text_dim']} !important;
    font-size: 0.91rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}}
div[data-testid="stMetricLabel"] {{
    color: {HUD['text_dim']} !important;
    font-size: 0.91rem !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    white-space: normal !important;
}}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: {HUD['text']} !important;
    font-size: 1.49rem !important;
    font-weight: 700 !important;
    line-height: 1.12 !important;
    font-variant-numeric: tabular-nums !important;
    white-space: normal !important;
    overflow-wrap: anywhere !important;
}}
div[data-testid="stMetricValue"] {{
    color: {HUD['text']} !important;
    font-size: 1.49rem !important;
    font-weight: 800 !important;
    line-height: 1.12 !important;
    font-variant-numeric: tabular-nums !important;
    white-space: normal !important;
    overflow-wrap: anywhere !important;
}}
div[data-testid="stMetricValue"] * {{
    font-size: 1.49rem !important;
    line-height: 1.12 !important;
    white-space: normal !important;
    overflow-wrap: anywhere !important;
}}
div[data-testid="metric-container"] [data-testid="stMetricValue"] * {{
    font-size: 1.49rem !important;
    line-height: 1.12 !important;
    white-space: normal !important;
    overflow-wrap: anywhere !important;
}}
div[data-testid="metric-container"] [data-testid="stMetricDelta"] {{
    color: {HUD['green']} !important;
    font-size: 1.01rem !important;
    white-space: normal !important;
}}
div[data-testid="stMetricDelta"] {{
    color: {HUD['green']} !important;
    font-size: 1.01rem !important;
    white-space: normal !important;
}}

/* ── Plotly charts ─────────────────────────────────────────────────────── */
.js-plotly-plot .plotly .bg {{
    fill: transparent !important;
}}

/* ── Dataframes ─────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {{
    border: 1px solid {HUD['border']} !important;
    border-radius: 4px !important;
    overflow: hidden !important;
}}

/* ── Tabs ──────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab"] {{
    color: {HUD['text_dim']} !important;
    border-bottom: 2px solid transparent !important;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    color: {HUD['cyan']} !important;
    border-bottom: 2px solid {HUD['cyan']} !important;
    text-shadow: {HUD['glow']} !important;
}}

/* ── Buttons ───────────────────────────────────────────────────────────── */
[data-testid="baseButton-primary"],
[data-testid="baseButton-secondary"] {{
    background: linear-gradient(180deg, #161616, #070707) !important;
    border: 1px solid {HUD['border']} !important;
    color: {HUD['text']} !important;
    border-radius: 0 !important;
    transition: border-color 0.12s ease, background 0.12s ease !important;
    font-family: 'IBM Plex Mono', 'SF Mono', 'Menlo', monospace !important;
    font-weight: 800 !important;
    letter-spacing: 0.03em !important;
    text-transform: uppercase !important;
}}
[data-testid="baseButton-primary"]:hover,
[data-testid="baseButton-secondary"]:hover {{
    background: {HUD['surface_hover']} !important;
    border-color: {HUD['amber']} !important;
}}

/* ── Inputs / Selects ──────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stSelectbox"] div,
[data-testid="stMultiSelect"] div {{
    background: {HUD['surface']} !important;
    border-color: {HUD['border']} !important;
    color: {HUD['text']} !important;
    border-radius: 0 !important;
    font-family: 'IBM Plex Mono', 'SF Mono', 'Menlo', monospace !important;
}}
[data-testid="stCheckbox"] label,
[data-testid="stToggle"] label,
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label,
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stDateInput"] label {{
    color: {HUD['text_dim']} !important;
    font-family: 'IBM Plex Mono', 'SF Mono', 'Menlo', monospace !important;
    font-size: 0.91rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}}
[data-testid="stForm"] {{
    background: #050505 !important;
    border: 1px solid {HUD['border']} !important;
    border-radius: 0 !important;
    padding: 8px !important;
}}
[data-testid="stAlert"] {{
    background: #080808 !important;
    border: 1px solid {HUD['border']} !important;
    border-radius: 0 !important;
    color: {HUD['gold']} !important;
}}
[data-testid="stAlert"] * {{
    color: inherit !important;
}}

/* ── Dividers ──────────────────────────────────────────────────────────── */
hr {{
    border: none !important;
    border-top: 1px solid {HUD['border']} !important;
    opacity: 1 !important;
}}

/* ── Expanders ─────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {{
    background: {HUD['surface']} !important;
    border: 1px solid {HUD['border']} !important;
    border-radius: 0 !important;
}}
[data-testid="stExpander"] summary {{
    background: linear-gradient(90deg, #A90E24, #111) !important;
    color: {HUD['text']} !important;
    font-family: 'IBM Plex Mono', 'SF Mono', 'Menlo', monospace !important;
    font-weight: 800 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
}}

/* ── Scrollbars ─────────────────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: {HUD['bg']}; }}
::-webkit-scrollbar-thumb {{ background: {HUD['border']}; border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: {HUD['cyan']}; }}

/* ── HUD badges ─────────────────────────────────────────────────────────── */
.hud-badge {{
    display: inline-block;
    padding: 2px 7px;
    border-radius: 3px;
    font-size: 0.91rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    line-height: 1.6;
}}

/* ── Page title ─────────────────────────────────────────────────────────── */
h1 {{
    color: {HUD['text']} !important;
    text-shadow: none !important;
    letter-spacing: 0.02em !important;
}}
h2, h3 {{
    color: {HUD['text']} !important;
    border-bottom: 1px solid {HUD['border']};
    padding-bottom: 0.25rem;
    font-family: 'IBM Plex Mono', 'SF Mono', 'Menlo', monospace !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
}}
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] * {{
    color: {HUD['text_dim']} !important;
    font-family: 'IBM Plex Mono', 'SF Mono', 'Menlo', monospace !important;
    letter-spacing: 0.02em !important;
}}
.stMarkdown table {{
    width: 100%;
    border-collapse: collapse;
    background: #050505;
    border: 1px solid {HUD['border']};
    font-size: 0.97rem;
    font-variant-numeric: tabular-nums;
}}
.stMarkdown th {{
    position: sticky;
    top: 0;
    background: #D07A00;
    color: #080808;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 0.89rem;
    font-weight: 900;
    padding: 5px 7px;
    border: 1px solid #2B2B2B;
}}
.stMarkdown td {{
    padding: 4px 7px;
    border: 1px solid rgba(114,114,114,0.32);
    color: {HUD['text']};
    font-variant-numeric: tabular-nums;
}}
.stMarkdown tr:nth-child(even) td {{
    background: #0D0D0D;
}}
.stMarkdown td:nth-child(n+3) {{
    color: {HUD['gold']};
    text-align: right;
}}
.stMarkdown tr:hover td {{
    background: rgba(255,159,26,0.10);
}}
</style>
""", unsafe_allow_html=True)


def render_hud_topbar(page_title: str, page_icon: str = "") -> None:
    """
    Render the futuristic System HUD top bar with live timestamp and status pills.
    Call after inject_hud_css() and before the main page content.
    """
    now = datetime.now()
    ts  = now.strftime("%Y-%m-%d  %H:%M:%S")
    weekday = now.strftime("%A").upper()

    st.markdown(f"""
<div style="
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(0,212,255,0.04);
    border: 1px solid {HUD['border']};
    border-radius: 12px;
    padding: 10px 20px;
    margin-bottom: 20px;
    backdrop-filter: blur(16px);
    box-shadow: {HUD['glow']};
">
  <div style="display:flex; align-items:center; gap:14px;">
    <span style="font-size:1.65rem; line-height:1;">{page_icon}</span>
    <div>
      <div style="
        font-size: 1.3rem;
        font-weight: 700;
        color: {HUD['cyan']};
        text-shadow: {HUD['glow']};
        letter-spacing: 0.06em;
        text-transform: uppercase;
      ">SYSTEM HUD · {page_title.upper()}</div>
      <div style="font-size: 0.97rem; color: {HUD['text_dim']}; letter-spacing: 0.1em;">
        FulôFiló AI · LOCAL-FIRST · iMac M3
      </div>
    </div>
  </div>

  <div style="display:flex; align-items:center; gap:12px;">
    <div style="
        background: rgba(0,255,136,0.10);
        border: 1px solid {HUD['green']};
        border-radius: 6px;
        padding: 3px 10px;
        font-size: 0.95rem;
        color: {HUD['green']};
        letter-spacing: 0.08em;
        text-shadow: {HUD['glow_green']};
    ">● ONLINE</div>
    <div style="
        background: rgba(0,212,255,0.08);
        border: 1px solid {HUD['border']};
        border-radius: 6px;
        padding: 3px 12px;
        font-size: 0.95rem;
        color: {HUD['text_dim']};
        letter-spacing: 0.06em;
        font-variant-numeric: tabular-nums;
    ">{weekday} · {ts}</div>
  </div>
</div>
""", unsafe_allow_html=True)


def abc_badge(cls: str) -> str:
    """
    Return an HTML span badge for an ABC class (A / B / C).
    Embed inside st.markdown(..., unsafe_allow_html=True).
    """
    bg, fg, glow = ABC_STYLE.get(cls, ("#2D3748", HUD["text_dim"], "none"))
    label = f"CLASS {cls}"
    return (
        f'<span class="hud-badge" style="'
        f"background:{bg}; color:{fg}; "
        f'box-shadow:{glow};">{label}</span>'
    )


def alert_badge(alert: str) -> str:
    """
    Return an HTML span badge for an inventory alert status.
    alert: one of 'Crítico', 'Baixo', 'OK'
    """
    normalized = (
        str(alert)
        .replace("\U0001f534 ", "")
        .replace("\U0001f7e1 ", "")
        .replace("\U0001f7e2 ", "")
        .strip()
    )
    bg, fg, glow = ALERT_STYLE.get(normalized, ("#2D3748", HUD["text_dim"], "none"))
    label = normalized.upper()
    return (
        f'<span class="hud-badge" style="'
        f"background:{bg}; color:{fg}; "
        f'box-shadow:{glow};">{label}</span>'
    )


def conf_badge(conf: str) -> str:
    """
    Return an HTML span badge for CategoryConfidence values.
    conf: 'high', 'medium', 'low', 'unmatched', 'manual'
    """
    bg, fg = CONF_STYLE.get(conf, ("#2D3748", HUD["text_dim"]))
    return (
        f'<span class="hud-badge" style="'
        f'background:{bg}; color:{fg};">{conf.upper()}</span>'
    )


def action_tag_badge(tag: str) -> str:
    """
    Return an HTML span badge for an ABC action tag.
    tag: one of "SCALE", "OPTIMIZE", "REDUCE"
    """
    normalized = (
        str(tag)
        .replace("\U0001f525 ", "")
        .replace("\u2699\ufe0f ", "")
        .replace("\U0001f9f9 ", "")
        .strip()
    )
    bg, fg, glow = ACTION_TAG_STYLE.get(normalized, ("#2D3748", HUD["text_dim"], "none"))
    return (
        f'<span class="hud-badge" style="'
        f"background:{bg}; color:{fg}; "
        f'box-shadow:{glow};">{normalized}</span>'
    )


def priority_badge(priority: str) -> str:
    """
    Return an HTML span badge for a decision priority level.
    priority: "HIGH", "MEDIUM", or "LOW"
    """
    bg, fg, glow = PRIORITY_STYLE.get(priority, ("#2D3748", HUD["text_dim"], "none"))
    return (
        f'<span class="hud-badge" style="'
        f"background:{bg}; color:{fg}; "
        f'box-shadow:{glow};">{priority}</span>'
    )


def hud_plotly_layout(fig, height: int = 460) -> None:
    """
    Apply HUD-consistent dark theming to a Plotly figure in-place.
    Call before st.plotly_chart().
    """
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#050505",
        font=dict(color=HUD["text"], family="IBM Plex Mono, SF Mono, Menlo, monospace", size=11),
        xaxis=dict(
            gridcolor="rgba(255,159,26,0.12)",
            linecolor=HUD["border"],
            zerolinecolor="rgba(255,159,26,0.16)",
            tickfont=dict(color=HUD["text_dim"], size=10),
        ),
        yaxis=dict(
            gridcolor="rgba(255,159,26,0.12)",
            linecolor=HUD["border"],
            zerolinecolor="rgba(255,159,26,0.16)",
            tickfont=dict(color=HUD["text_dim"], size=10),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=HUD["border"],
        ),
    )
