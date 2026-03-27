"""
FulôFiló — 📤 Export Excel (Page 6)
=====================================
Generate and download the full Excel workbook on demand.
"""

import sys
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="Exportar Excel — FulôFiló", page_icon="📤", layout="wide")
st.markdown("## 📤 Exportar Relatório Excel")
st.caption("Gera o workbook completo com 9 abas a partir dos dados atuais em Parquet.")

# ── Sheet selector ─────────────────────────────────────────────────────────────
st.subheader("📋 Selecionar abas")
SHEETS = ["Dashboard","ABC Analysis","Margin Matrix","Inventory",
          "Daily Ops","Cashflow","Products Catalog","Product Categories","Pivot Cat×Month"]
col1, col2 = st.columns(2)
selected = {}
for i, s in enumerate(SHEETS):
    col = col1 if i < 5 else col2
    selected[s] = col.checkbox(s, value=True)

st.divider()

# ── Generate button ────────────────────────────────────────────────────────────
if st.button("⚡ Gerar Relatório", type="primary", use_container_width=True):
    bar = st.progress(0, text="Inicializando...")
    try:
        bar.progress(10, "Carregando dados Parquet...")
        sys.path.insert(0, str(ROOT))
        from excel.build_report import build_report
        bar.progress(30, "Construindo abas...")
        t0 = time.time()
        out_path = build_report()
        elapsed  = time.time() - t0
        bar.progress(100, "✅ Concluído!")

        size_kb = out_path.stat().st_size // 1024
        st.success(f"Relatório gerado em {elapsed:.1f}s — {size_kb} KB — {out_path.name}")

        c1, c2, c3 = st.columns(3)
        c1.metric("Abas", len(SHEETS))
        c2.metric("Tamanho", f"{size_kb} KB")
        c3.metric("Tempo geração", f"{elapsed:.1f}s")

        st.download_button(
            label="📥 Baixar Excel",
            data=out_path.read_bytes(),
            file_name=out_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    except Exception as exc:
        bar.progress(0, "Erro!")
        st.error(f"Falha na geração: {exc}")
        st.exception(exc)

# ── History ────────────────────────────────────────────────────────────────────
st.divider()
st.subheader("🗂️ Relatórios anteriores")
excel_dir = ROOT / "excel"
reports = sorted(excel_dir.glob("FuloFilo_Report_*.xlsx"), reverse=True)[:5]
if reports:
    for rpt in reports:
        size_kb = rpt.stat().st_size // 1024
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.markdown(f"📄 `{rpt.name}`")
        c2.caption(f"{size_kb} KB")
        c3.download_button("⬇", data=rpt.read_bytes(), file_name=rpt.name,
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key=rpt.name)
else:
    st.info("Nenhum relatório gerado ainda. Clique em 'Gerar Relatório' acima.")
