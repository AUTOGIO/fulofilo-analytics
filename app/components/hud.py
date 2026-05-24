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
    "bg":          "#050809",
    "sidebar_bg":  "#07100E",
    "surface":     "rgba(13,24,23,0.92)",
    "surface_hover": "rgba(18,44,41,0.95)",
    "cyan":        "#37D5E8",
    "green":       "#35D07F",
    "gold":        "#C9A35A",
    "red":         "#E05252",
    "amber":       "#D89B3D",
    "navy":        "#08111F",
    "graphite":    "#0B0F10",
    "muted":       "#4A5568",
    "text":        "#DCE6E3",
    "text_dim":    "#82908C",
    "border":      "rgba(87,113,108,0.34)",
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
    "🔴 Crítico": (HUD["red"],   "#fff",    HUD["glow_red"]),
    "🟡 Baixo":   (HUD["gold"],  "#080C18", "0 0 14px rgba(255,215,0,0.35)"),
    "🟢 OK":      (HUD["green"], "#080C18", HUD["glow_green"]),
}

# Action tag (ABC decision) → (bg, text, glow)
ACTION_TAG_STYLE: dict[str, tuple[str, str, str]] = {
    "🔥 SCALE":    (HUD["green"], "#080C18", HUD["glow_green"]),
    "⚙️ OPTIMIZE": (HUD["gold"],  "#080C18", "0 0 14px rgba(255,215,0,0.35)"),
    "🧹 REDUCE":   (HUD["red"],   "#fff",    HUD["glow_red"]),
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
        linear-gradient(180deg, rgba(8,17,31,0.52) 0%, rgba(5,8,9,0.94) 42%),
        repeating-linear-gradient(0deg, rgba(255,255,255,0.020) 0, rgba(255,255,255,0.020) 1px, transparent 1px, transparent 28px),
        {HUD['bg']} !important;
    color: {HUD['text']};
    font-family: 'Inter', 'SF Pro Text', 'Segoe UI', system-ui, sans-serif;
}}
.block-container {{
    max-width: 1920px !important;
    padding: 0.75rem 1rem 3rem !important;
}}

/* ── Sidebar ───────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #07100E 0%, #050809 100%) !important;
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
    background: linear-gradient(180deg, rgba(15,28,27,0.96), rgba(8,14,15,0.96)) !important;
    border: 1px solid {HUD['border']} !important;
    border-radius: 4px !important;
    padding: 0.72rem 0.82rem !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03) !important;
}}
div[data-testid="metric-container"] [data-testid="stMetricLabel"] {{
    color: {HUD['text_dim']} !important;
    font-size: 0.66rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: {HUD['text']} !important;
    font-size: 1.22rem !important;
    font-weight: 700 !important;
    font-variant-numeric: tabular-nums !important;
}}
div[data-testid="metric-container"] [data-testid="stMetricDelta"] {{
    color: {HUD['green']} !important;
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
    background: #0B1515 !important;
    border: 1px solid {HUD['border']} !important;
    color: {HUD['text']} !important;
    border-radius: 4px !important;
    transition: border-color 0.12s ease, background 0.12s ease !important;
}}
[data-testid="baseButton-primary"]:hover,
[data-testid="baseButton-secondary"]:hover {{
    background: {HUD['surface_hover']} !important;
    border-color: {HUD['cyan']} !important;
}}

/* ── Inputs / Selects ──────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] div,
[data-testid="stMultiSelect"] div {{
    background: {HUD['surface']} !important;
    border-color: {HUD['border']} !important;
    color: {HUD['text']} !important;
    border-radius: 4px !important;
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
    border-radius: 4px !important;
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
    font-size: 0.66rem;
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
}}
.stMarkdown table {{
    width: 100%;
    border-collapse: collapse;
    background: rgba(7,12,13,0.74);
    border: 1px solid {HUD['border']};
    font-size: 0.78rem;
}}
.stMarkdown th {{
    position: sticky;
    top: 0;
    background: #101A1A;
    color: {HUD['text_dim']};
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.65rem;
    padding: 6px 8px;
    border-bottom: 1px solid {HUD['border']};
}}
.stMarkdown td {{
    padding: 5px 8px;
    border-bottom: 1px solid rgba(87,113,108,0.18);
    color: {HUD['text']};
    font-variant-numeric: tabular-nums;
}}
.stMarkdown tr:hover td {{
    background: rgba(55,213,232,0.045);
}}
</style>
""", unsafe_allow_html=True)


def render_hud_topbar(page_title: str, page_icon: str = "◈") -> None:
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
    <span style="font-size:1.4rem; line-height:1;">{page_icon}</span>
    <div>
      <div style="
        font-size: 1.05rem;
        font-weight: 700;
        color: {HUD['cyan']};
        text-shadow: {HUD['glow']};
        letter-spacing: 0.06em;
        text-transform: uppercase;
      ">SYSTEM HUD · {page_title.upper()}</div>
      <div style="font-size: 0.72rem; color: {HUD['text_dim']}; letter-spacing: 0.1em;">
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
        font-size: 0.70rem;
        color: {HUD['green']};
        letter-spacing: 0.08em;
        text-shadow: {HUD['glow_green']};
    ">● ONLINE</div>
    <div style="
        background: rgba(0,212,255,0.08);
        border: 1px solid {HUD['border']};
        border-radius: 6px;
        padding: 3px 12px;
        font-size: 0.70rem;
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
    alert: one of '🔴 Crítico', '🟡 Baixo', '🟢 OK'
    """
    bg, fg, glow = ALERT_STYLE.get(alert, ("#2D3748", HUD["text_dim"], "none"))
    label_map = {"🔴 Crítico": "CRÍTICO", "🟡 Baixo": "BAIXO", "🟢 OK": "OK"}
    label = label_map.get(alert, alert)
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
    tag: one of "🔥 SCALE", "⚙️ OPTIMIZE", "🧹 REDUCE"
    """
    bg, fg, glow = ACTION_TAG_STYLE.get(tag, ("#2D3748", HUD["text_dim"], "none"))
    return (
        f'<span class="hud-badge" style="'
        f"background:{bg}; color:{fg}; "
        f'box-shadow:{glow};">{tag}</span>'
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
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=HUD["text"], family="Inter, Segoe UI, sans-serif"),
        xaxis=dict(
            gridcolor="rgba(0,212,255,0.08)",
            linecolor=HUD["border"],
            zerolinecolor="rgba(0,212,255,0.12)",
        ),
        yaxis=dict(
            gridcolor="rgba(0,212,255,0.08)",
            linecolor=HUD["border"],
            zerolinecolor="rgba(0,212,255,0.12)",
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=HUD["border"],
        ),
    )
