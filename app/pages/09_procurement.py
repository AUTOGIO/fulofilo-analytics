import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
_FAVICON = str(Path(__file__).resolve().parent.parent / "assets" / "favicon.png")
sys.path.insert(0, str(ROOT))
from app.db import get_conn, get_data_mtime
from app.components.sidebar import render_sidebar
from app.components.hud import inject_hud_css
from app.components.terminal import page_command_header, render_terminal_css
from core.procurement.purchase_order import export_po_artifacts, generate_po_drafts
from core.ops_memory import log_decision
from app.utils.procurement_ops import append_po_to_excel

st.set_page_config(page_title="Procurement — FulôFiló", page_icon=_FAVICON, layout="wide")
inject_hud_css()
render_terminal_css()
render_sidebar()
page_command_header("Procurement", "PO / suppliers", "review PO drafts -> approve -> Excel master")

@st.cache_data
def load(data_version: str):
    conn = get_conn()
    try:
        drafts = generate_po_drafts(conn)
    finally:
        conn.close()
    return drafts

drafts = load(get_data_mtime())

if not drafts:
    st.info("Nenhum rascunho de PO no momento — estoque dentro dos limiares dinâmicos.")
    if st.button("Gerar artefatos PO"):
        conn = get_conn()
        try:
            export_po_artifacts(conn)
        finally:
            conn.close()
        st.success("Artefatos gravados em data/outputs/purchase_orders/")
        st.rerun()
    st.stop()

for po in drafts:
    with st.expander(f"{po['po_id']} — {po['supplier_name']} (R$ {po['po_total_brl']:,.2f})", expanded=True):
        st.dataframe(po["lines"], width="stretch", hide_index=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Aprovar PO", key=f"approve_{po['po_id']}"):
                try:
                    result = append_po_to_excel(po, status="approved")
                    log_decision(
                        alert_type="PROCUREMENT",
                        action_taken="APPROVE_PO",
                        sku="",
                        product=po["supplier_name"],
                        alert_priority="HIGH",
                        notes=f"{result.lines_written} linhas -> {result.backup_path}",
                    )
                    st.success(f"PO aprovado ({result.lines_written} linhas). Execute sync para atualizar read models.")
                except Exception as exc:
                    st.error(str(exc))
        with c2:
            if st.button("Ignorar", key=f"skip_{po['po_id']}"):
                log_decision(
                    alert_type="PROCUREMENT",
                    action_taken="SKIP_PO",
                    product=po["supplier_name"],
                    notes=po["po_id"],
                )
                st.toast("Decisão registrada em ops_decisions.csv")

st.divider()
if st.button("Exportar JSON + Excel"):
    conn = get_conn()
    try:
        out = export_po_artifacts(conn)
    finally:
        conn.close()
    st.json(json.loads(Path(out["json_path"]).read_text(encoding="utf-8")))
