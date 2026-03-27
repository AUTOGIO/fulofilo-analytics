"""
FulôFiló — Shared Sidebar with Logo
=====================================
Import and call render_sidebar() from every page to get a
consistent logo + navigation across the entire app.
"""

from pathlib import Path
import streamlit as st

ASSETS = Path(__file__).resolve().parent.parent / "assets"
LOGO_FULL   = str(ASSETS / "logo.png")
LOGO_SMALL  = str(ASSETS / "favicon.png")


def inject_logo():
    """
    Pin the FulôFiló logo at the top of the sidebar using st.logo().
    Call this once per page — before any st.sidebar content.
    Works on Streamlit >= 1.35.
    """
    st.logo(
        image=LOGO_FULL,
        icon_image=LOGO_SMALL,   # shown when sidebar is collapsed
        link="http://127.0.0.1:8501",
        size="large",
    )


def render_sidebar(active_page: str = ""):
    """
    Render logo + full navigation sidebar.
    Args:
        active_page: filename of the current page (e.g. 'app.py')
    """
    inject_logo()

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📋 Navegação")
        st.page_link("app.py",                   label="🏠 Visão Geral")
        st.page_link("pages/01_abc_analysis.py",  label="📊 Análise ABC")
        st.page_link("pages/02_margin_matrix.py", label="💹 Matriz de Margem")
        st.page_link("pages/03_inventory.py",     label="📦 Estoque")
        st.page_link("pages/04_daily_ops.py",     label="⚡ Operações Diárias")
        st.page_link("pages/05_categories.py",    label="🏷️ Categorias")
        st.page_link("pages/06_export_excel.py",  label="📤 Exportar Excel")
        st.markdown("---")
        st.caption("🌺 FulôFiló Analytics Pro")
        st.caption("iMac M3 · macOS 26.4 · local-first")
