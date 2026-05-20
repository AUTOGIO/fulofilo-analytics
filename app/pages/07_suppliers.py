"""
FulôFiló — Fornecedores (Terminal Edition)
===========================================
Embeds the suppliers dashboard HTML inline and provides
a one-click button to open it in the default browser.

Run: uv run streamlit run app/app.py  →  navigate via sidebar
"""

import subprocess
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.components.sidebar import render_sidebar, render_page_header
from app.components.terminal import inject_terminal_css, render_terminal_header

# ── Page config ───────────────────────────────────────────────────────────────
_FAVICON = str(Path(__file__).resolve().parent.parent / "assets" / "favicon.png")
st.set_page_config(
    page_title="FulôFiló — Fornecedores",
    page_icon=_FAVICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_terminal_css()
render_sidebar(active_page="pages/07_suppliers.py")
render_page_header()
render_terminal_header("Fornecedores", "🏭")

# ── Paths ─────────────────────────────────────────────────────────────────────
_ROOT          = Path(__file__).resolve().parent.parent.parent
_HTML_FILE     = _ROOT / "data" / "suppliers" / "suppliers_dashboard.html"
_SUPPLIERS_DIR = _ROOT / "data" / "suppliers"
_SUPPLIERS_DB  = _SUPPLIERS_DIR / "SUPPLIERS_DB.xlsx"
_SUPPLIERS_PDF = _SUPPLIERS_DIR / "ALL_SUPPLIERS_COMPLETE.pdf"

# ── Action buttons ────────────────────────────────────────────────────────────
col_open, col_xlsx, col_pdf, col_folder, _ = st.columns([1.4, 1, 1, 1, 2])

with col_open:
    if st.button("🌐 Abrir no Browser", use_container_width=True,
                 help="Abre suppliers_dashboard.html no browser padrão (macOS)"):
        if _HTML_FILE.exists():
            subprocess.run(["open", str(_HTML_FILE)])
            st.success("Abrindo no browser…")
        else:
            st.error(f"Arquivo não encontrado: {_HTML_FILE}")

with col_xlsx:
    if st.button("📊 SUPPLIERS_DB.xlsx", use_container_width=True,
                 help="Abre planilha de fornecedores"):
        if _SUPPLIERS_DB.exists():
            subprocess.run(["open", str(_SUPPLIERS_DB)])
        else:
            st.warning("SUPPLIERS_DB.xlsx não encontrado.")

with col_pdf:
    if st.button("📄 PDF Completo", use_container_width=True,
                 help="Abre ALL_SUPPLIERS_COMPLETE.pdf"):
        if _SUPPLIERS_PDF.exists():
            subprocess.run(["open", str(_SUPPLIERS_PDF)])
        else:
            st.warning("PDF não encontrado.")

with col_folder:
    if st.button("📂 Abrir Pasta", use_container_width=True,
                 help="Abre data/suppliers/ no Finder"):
        subprocess.run(["open", str(_SUPPLIERS_DIR)])

st.divider()

# ── Inline embed ──────────────────────────────────────────────────────────────
if _HTML_FILE.exists():
    html_content = _HTML_FILE.read_text(encoding="utf-8")
    st.components.v1.html(html_content, height=820, scrolling=True)
else:
    st.error(
        f"Dashboard de fornecedores não encontrado em:\n`{_HTML_FILE}`\n\n"
        "Execute o pipeline de fornecedores ou verifique o caminho."
    )
