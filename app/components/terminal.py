"""
FulôFiló Trading Terminal Theme
═══════════════════════════════════════════════════════════════════════════════
Professional trading terminal aesthetic with FulôFiló brand colors.
Replaces HUD system for sleek, data-centric dashboard.

Brand Colors:
  Primary Dark Teal:   #004739 (RGB: 0, 71, 57)
  Accent Brown:        #682C0E (RGB: 104, 44, 14)
  Accent Lime:         #8FD929 (RGB: 143, 217, 41)
  Accent Cyan:         #00C9E6 (RGB: 0, 201, 230)
  Accent Red/Coral:    #F55C47 (RGB: 245, 92, 71)
"""

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL THEME PALETTE
# ─────────────────────────────────────────────────────────────────────────────
TERMINAL = {
    # Brand colors
    "bg_dark":        "#0a0e27",          # Near-black terminal background
    "primary_teal":   "#004739",          # FulôFiló primary dark teal
    "accent_brown":   "#682C0E",          # FulôFiló accent brown
    "accent_lime":    "#8FD929",          # FulôFiló accent lime (positive/healthy)
    "accent_cyan":    "#00C9E6",          # FulôFiló accent cyan (neutral data)
    "accent_red":     "#F55C47",          # FulôFiló accent red (critical/alerts)

    # Semantic colors
    "positive":       "#8FD929",          # Green: revenue up, margin healthy
    "negative":       "#F55C47",          # Red: losses, alerts, warnings
    "neutral":        "#00C9E6",          # Cyan: data, informational
    "warning":        "#FFB91C",          # Orange: caution
    "secondary":      "#682C0E",          # Brown: secondary information

    # UI colors
    "text_primary":   "#E8E8E8",          # Main text (light gray)
    "text_secondary": "#A8A8A8",          # Dimmed text (medium gray)
    "text_muted":     "#686868",          # Very dim text (dark gray)
    "border":         "rgba(255,255,255,0.08)",  # Subtle borders
    "border_bright":  "rgba(255,255,255,0.15)",  # Slightly visible borders

    # Chart colors
    "chart_a":        "#8FD929",          # ABC A class
    "chart_b":        "#FFB91C",          # ABC B class
    "chart_c":        "#F55C47",          # ABC C class
}

# ─────────────────────────────────────────────────────────────────────────────
# CSS INJECTION
# ─────────────────────────────────────────────────────────────────────────────
def inject_terminal_css():
    """Inject trading terminal CSS theme into Streamlit page."""
    css = f"""
    <style>
    :root {{
        --bg-dark: {TERMINAL['bg_dark']};
        --primary-teal: {TERMINAL['primary_teal']};
        --accent-cyan: {TERMINAL['accent_cyan']};
        --accent-lime: {TERMINAL['accent_lime']};
        --accent-red: {TERMINAL['accent_red']};
        --text-primary: {TERMINAL['text_primary']};
        --text-secondary: {TERMINAL['text_secondary']};
        --text-muted: {TERMINAL['text_muted']};
    }}

    /* ─ Page Background ─ */
    body, .main {{
        background-color: {TERMINAL['bg_dark']} !important;
        color: {TERMINAL['text_primary']};
    }}

    /* ─ Sidebar ─ */
    [data-testid="stSidebar"] {{
        background-color: rgba(0, 71, 57, 0.15) !important;
        border-right: 1px solid {TERMINAL['border_bright']};
    }}

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{
        color: {TERMINAL['text_primary']};
    }}

    /* ─ Metrics ─ */
    [data-testid="metric-container"] {{
        background: linear-gradient(135deg, rgba(0,71,57,0.3) 0%, rgba(0,201,230,0.05) 100%);
        border: 1px solid {TERMINAL['border_bright']};
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }}

    [data-testid="metric-container"] [data-testid="stMetricValue"] {{
        color: {TERMINAL['accent_cyan']};
        font-family: 'Monaco', 'Courier New', monospace;
        font-weight: 700;
        letter-spacing: 0.05em;
    }}

    [data-testid="metric-container"] [data-testid="stMetricLabel"] {{
        color: {TERMINAL['text_secondary']};
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }}

    /* ─ Headers ─ */
    h1, h2, h3, h4, h5, h6 {{
        color: {TERMINAL['text_primary']};
        border-bottom: 2px solid {TERMINAL['border_bright']};
        padding-bottom: 8px;
        margin-bottom: 12px;
    }}

    h1 {{
        color: {TERMINAL['accent_cyan']};
        text-shadow: 0 0 10px rgba(0, 201, 230, 0.3);
        font-size: 1.8rem;
    }}

    h2 {{
        color: {TERMINAL['accent_lime']};
        border-color: {TERMINAL['accent_lime']};
        font-size: 1.3rem;
    }}

    h3 {{
        color: {TERMINAL['text_primary']};
        border-color: {TERMINAL['accent_cyan']};
        font-size: 1.1rem;
    }}

    /* ─ Dividers ─ */
    [data-testid="stHorizontalBlock"] hr {{
        border-color: {TERMINAL['border_bright']} !important;
        margin: 20px 0;
    }}

    /* ─ Expanders ─ */
    [data-testid="stExpander"] {{
        border: 1px solid {TERMINAL['border_bright']} !important;
        background-color: rgba(0, 71, 57, 0.1) !important;
        border-radius: 6px;
    }}

    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] {{
        color: {TERMINAL['text_primary']};
    }}

    /* ─ Data Tables ─ */
    [data-testid="stTable"] {{
        font-family: 'Monaco', 'Courier New', monospace;
        font-size: 0.85rem;
    }}

    [data-testid="stTable"] table {{
        background-color: rgba(0,71,57,0.15) !important;
        border: 1px solid {TERMINAL['border_bright']} !important;
    }}

    [data-testid="stTable"] thead {{
        background-color: rgba(0, 201, 230, 0.08) !important;
        border-bottom: 2px solid {TERMINAL['accent_cyan']} !important;
    }}

    [data-testid="stTable"] th {{
        color: {TERMINAL['accent_cyan']} !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
        font-size: 0.7rem;
    }}

    [data-testid="stTable"] td {{
        color: {TERMINAL['text_primary']};
        border-color: {TERMINAL['border']} !important;
        padding: 10px 12px;
    }}

    /* ─ Code Blocks ─ */
    code {{
        background-color: rgba(0, 71, 57, 0.3);
        border: 1px solid {TERMINAL['border']};
        border-radius: 4px;
        padding: 2px 6px;
        color: {TERMINAL['accent_lime']};
        font-family: 'Monaco', 'Courier New', monospace;
    }}

    pre {{
        background-color: rgba(0, 0, 0, 0.4) !important;
        border: 1px solid {TERMINAL['border_bright']} !important;
        border-radius: 6px;
    }}

    /* ─ Buttons ─ */
    button {{
        background-color: {TERMINAL['primary_teal']} !important;
        color: {TERMINAL['text_primary']} !important;
        border: 1px solid {TERMINAL['accent_cyan']} !important;
        border-radius: 4px;
        font-weight: 600;
        transition: all 0.2s ease;
    }}

    button:hover {{
        background-color: {TERMINAL['accent_cyan']} !important;
        color: {TERMINAL['bg_dark']} !important;
        box-shadow: 0 0 12px rgba(0, 201, 230, 0.4);
    }}

    /* ─ Input Fields ─ */
    input, select, textarea {{
        background-color: rgba(0, 71, 57, 0.2) !important;
        border: 1px solid {TERMINAL['border_bright']} !important;
        color: {TERMINAL['text_primary']} !important;
        border-radius: 4px;
    }}

    input:focus, select:focus, textarea:focus {{
        border-color: {TERMINAL['accent_cyan']} !important;
        box-shadow: 0 0 8px rgba(0, 201, 230, 0.2);
    }}

    /* ─ Captions & Helper Text ─ */
    [data-testid="stCaptionContainer"] {{
        color: {TERMINAL['text_secondary']};
    }}

    .stAlert, [data-testid="stAlert"] {{
        background-color: rgba(0, 71, 57, 0.2);
        border-left: 4px solid {TERMINAL['accent_lime']};
        color: {TERMINAL['text_primary']};
    }}

    /* ─ Terminal-style text ─ */
    .terminal-value {{
        font-family: 'Monaco', 'Courier New', monospace;
        font-weight: 700;
        color: {TERMINAL['accent_cyan']};
        letter-spacing: 0.05em;
    }}

    .terminal-label {{
        font-family: 'Monaco', 'Courier New', monospace;
        font-size: 0.7rem;
        color: {TERMINAL['text_muted']};
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }}

    .positive-value {{
        color: {TERMINAL['accent_lime']};
        font-weight: 700;
    }}

    .negative-value {{
        color: {TERMINAL['accent_red']};
        font-weight: 700;
    }}

    .neutral-value {{
        color: {TERMINAL['accent_cyan']};
        font-weight: 700;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL HEADER COMPONENT
# ─────────────────────────────────────────────────────────────────────────────
def render_terminal_header(title: str, icon: str = "📊"):
    """
    Render a trading terminal-style header.

    Args:
        title: Header text
        icon: Emoji icon
    """
    st.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 16px 0;
        border-bottom: 2px solid {TERMINAL['accent_cyan']};
        margin-bottom: 12px;
    ">
        <span style="font-size: 1.4rem;">{icon}</span>
        <h2 style="
            color: {TERMINAL['accent_cyan']};
            margin: 0;
            font-size: 1.3rem;
            letter-spacing: 0.05em;
            border: none;
            padding: 0;
        ">{title}</h2>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# KPI CARD COMPONENT
# ─────────────────────────────────────────────────────────────────────────────
def render_kpi_card(label: str, value: str, status: str = "neutral", icon: str = "📊"):
    """
    Render a single KPI card in terminal style.

    Args:
        label: KPI label (e.g., "Receita Total")
        value: KPI value (e.g., "R$ 50,000.00")
        status: "positive", "negative", or "neutral" (default)
        icon: Emoji icon
    """
    color_map = {
        "positive": TERMINAL["accent_lime"],
        "negative": TERMINAL["accent_red"],
        "neutral": TERMINAL["accent_cyan"],
        "warning": TERMINAL["warning"],
        "secondary": TERMINAL["accent_brown"],
    }
    color = color_map.get(status, TERMINAL["accent_cyan"])

    return f"""
    <div style="
        background: linear-gradient(135deg, rgba(0,71,57,0.25) 0%, rgba(0,201,230,0.08) 100%);
        border: 1px solid {TERMINAL['border_bright']};
        border-left: 4px solid {color};
        border-radius: 6px;
        padding: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        font-family: 'Monaco', 'Courier New', monospace;
    ">
        <div style="
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
        ">
            <span style="
                font-size: 0.7rem;
                color: {TERMINAL['text_muted']};
                text-transform: uppercase;
                letter-spacing: 0.1em;
                font-weight: 600;
            ">{icon} {label}</span>
        </div>
        <div style="
            font-size: 1.5rem;
            color: {color};
            font-weight: 700;
            letter-spacing: 0.05em;
        ">{value}</div>
    </div>
    """


# ─────────────────────────────────────────────────────────────────────────────
# PLOTLY CHART STYLING
# ─────────────────────────────────────────────────────────────────────────────
def terminal_plotly_layout(fig, height: int = 400):
    """
    Apply trading terminal styling to Plotly figure.

    Args:
        fig: Plotly figure
        height: Chart height in pixels
    """
    fig.update_layout(
        plot_bgcolor=TERMINAL["bg_dark"],
        paper_bgcolor=TERMINAL["bg_dark"],
        font=dict(
            family="Monaco, Courier New, monospace",
            color=TERMINAL["text_primary"],
            size=11,
        ),
        height=height,
        margin=dict(l=50, r=20, t=30, b=40),
        hovermode="x unified",
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=f"rgba(255,255,255,0.05)",
            zeroline=False,
            color=TERMINAL["text_secondary"],
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=f"rgba(255,255,255,0.05)",
            zeroline=False,
            color=TERMINAL["text_secondary"],
        ),
    )

    fig.update_xaxes(showline=True, linewidth=1, linecolor=TERMINAL["border"])
    fig.update_yaxes(showline=True, linewidth=1, linecolor=TERMINAL["border"])

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# STATUS BADGE
# ─────────────────────────────────────────────────────────────────────────────
def render_status_badge(status: str, count: int = None) -> str:
    """
    Render a status badge.

    Args:
        status: "critical", "warning", "healthy", "neutral"
        count: Optional count to display

    Returns:
        HTML string
    """
    colors = {
        "critical": TERMINAL["accent_red"],
        "warning": TERMINAL["warning"],
        "healthy": TERMINAL["accent_lime"],
        "neutral": TERMINAL["accent_cyan"],
    }

    icons = {
        "critical": "🔴",
        "warning": "🟠",
        "healthy": "🟢",
        "neutral": "🔵",
    }

    color = colors.get(status, TERMINAL["accent_cyan"])
    icon = icons.get(status, "•")
    count_str = f" ×{count}" if count else ""

    return f"""
    <span style="
        display: inline-block;
        background: rgba({color.replace('#', '0x')[0:7]}, 0.15);
        border: 1px solid {color};
        border-radius: 3px;
        padding: 3px 8px;
        font-size: 0.75rem;
        font-weight: 600;
        color: {color};
        margin-right: 4px;
    ">{icon} {status.upper()}{count_str}</span>
    """
