"""
FulôFiló — Shared Sidebar with Logo (HUD Edition)
===================================================
Import and call render_sidebar() from every page to get a
consistent logo + navigation across the entire app.
"""

from pathlib import Path
import streamlit as st
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

ASSETS = Path(__file__).resolve().parent.parent / "assets"
LOGO_FULL   = str(ASSETS / "logo.png")
LOGO_SMALL  = str(ASSETS / "favicon.png")
GMT_LOGO    = ASSETS / "GMT.png"
LOGO_17     = ASSETS / "Logo-17.png"
LOGO_44     = ASSETS / "Logo-44.jpg"

_NAV = [
    ("app.py",                   "🏠", "Visão Geral"),
    ("pages/01_abc_analysis.py",  "📊", "Análise ABC"),
    ("pages/02_margin_matrix.py", "💹", "Matriz de Margem"),
    ("pages/03_inventory.py",     "📦", "Estoque"),
    ("pages/04_daily_ops.py",     "⚡", "Operações Diárias"),
    ("pages/05_categories.py",    "🏷️", "Categorias"),
    ("pages/06_export_excel.py",  "📤", "Exportar Excel"),
]


def inject_logo():
    """
    Pin the FulôFiló logo at the top of the sidebar using st.logo().
    Call this once per page — before any st.sidebar content.
    Works on Streamlit >= 1.35.
    """
    st.logo(
        image=LOGO_FULL,
        icon_image=LOGO_SMALL,
        link="http://127.0.0.1:8501",
        size="large",
    )


def render_page_header(logo_path=None):
    """Render a logo centered at the top of any page's main content area.

    Args:
        logo_path: Path object or str to override the default Logo-17.
                   If None, falls back to LOGO_17.
    """
    target = Path(logo_path) if logo_path else LOGO_17
    if not target.exists():
        return
    _, col_center, _ = st.columns([2, 1, 2])
    with col_center:
        st.image(str(target), use_container_width=True)
    st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)


def get_selected_period() -> str:
    """Always returns 'ALL' — period filtering not active in current data model."""
    return "ALL"


def render_sidebar(active_page: str = ""):
    """
    Render logo + full HUD-styled navigation sidebar.
    Args:
        active_page: filename of the current page (e.g. 'app.py')
    """
    inject_logo()

    # HUD sidebar extra CSS (supplements hud.py global styles)
    st.markdown("""
<style>
[data-testid="stSidebar"] .stPageLink a {
    display: block;
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 0.88rem;
    letter-spacing: 0.03em;
    transition: background 0.2s, box-shadow 0.2s;
    text-decoration: none !important;
}
[data-testid="stSidebar"] .stPageLink a:hover {
    background: rgba(0,212,255,0.10) !important;
    box-shadow: 0 0 10px rgba(0,212,255,0.20);
}
.sidebar-section-label {
    font-size: 0.65rem;
    letter-spacing: 0.15em;
    color: #4A5568;
    text-transform: uppercase;
    padding: 4px 12px 2px;
    margin-top: 8px;
}
.sidebar-footer {
    font-size: 0.68rem;
    color: #4A5568;
    letter-spacing: 0.06em;
    text-align: center;
    padding: 8px 0 4px;
}
.sidebar-status-dot {
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #00FF88;
    box-shadow: 0 0 6px rgba(0,255,136,0.8);
    margin-right: 5px;
    vertical-align: middle;
}
</style>
""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown('<hr style="border-color:rgba(0,212,255,0.18);margin:4px 0 10px;">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section-label">◈ Navegação</div>', unsafe_allow_html=True)

        for page, icon, label in _NAV:
            st.page_link(page, label=f"{icon}  {label}")

        # ── Period label ───────────────────────────────────────────────────────
        st.markdown('<hr style="border-color:rgba(0,212,255,0.18);margin:10px 0 8px;">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section-label">◈ Período</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="text-align:center;font-size:0.75rem;color:#00D4FF;'
            'letter-spacing:0.06em;padding:6px 0;opacity:0.9;">'
            '📅 Mar – Abr 2026<br>'
            '<span style="font-size:0.68rem;color:#4A5568;">acumulado</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<hr style="border-color:rgba(0,212,255,0.18);margin:10px 0 8px;">', unsafe_allow_html=True)
        st.markdown(
            '<div class="sidebar-footer">'
            '<span class="sidebar-status-dot"></span>'
            'FulôFiló Analytics Pro<br>'
            'iMac M3 · macOS · local-first'
            '</div>',
            unsafe_allow_html=True,
        )

        # ── Sync & Deploy button (local only — no-op on Streamlit Cloud) ─────────
        import os, subprocess
        is_cloud = bool(os.environ.get("STREAMLIT_SHARING_MODE") or
                        os.environ.get("IS_STREAMLIT_CLOUD"))
        if not is_cloud:
            st.markdown('<hr style="border-color:rgba(0,212,255,0.10);margin:6px 0;">', unsafe_allow_html=True)
            st.markdown('<div class="sidebar-section-label">◈ Deploy</div>', unsafe_allow_html=True)
            if st.button("🚀 Sync & Push", use_container_width=True, help="Rebuilds parquets e faz git push → Streamlit redeploys"):
                sync_script = Path(__file__).resolve().parent.parent.parent / "etl" / "sync_and_push.py"
                with st.spinner("Sincronizando..."):
                    result = subprocess.run(
                        ["python3", str(sync_script), "--message", "manual sync via dashboard"],
                        capture_output=True, text=True,
                        cwd=str(sync_script.parent.parent),
                    )
                if result.returncode == 0:
                    st.success("✅ Push realizado! App atualiza em ~60s")
                else:
                    st.error(f"❌ Erro:\n{result.stderr[-300:]}")

        # ── GMT branding ───────────────────────────────────────────────────────
        if GMT_LOGO.exists():
            st.markdown(
                '<div class="sidebar-footer" style="margin-top:4px;">'
                'Develop by Giovannini Mare<br>Technology'
                '</div>',
                unsafe_allow_html=True,
            )
            st.image(str(GMT_LOGO), use_container_width=True)

