import subprocess
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.components.sidebar import render_sidebar
from app.components.hud import inject_hud_css
from app.components.terminal import page_command_header, render_terminal_css
from app.utils.supplier_desk import (
    DEFAULT_CONFIG,
    FILE_LINKS,
    load_supplier_desk,
    next_supplier_id,
    rebuild_supplier_dashboard,
    save_supplier_desk,
)

# ── Page config ───────────────────────────────────────────────────────────────
desk_data = load_supplier_desk()
desk_config = DEFAULT_CONFIG | desk_data.get("config", {})
_FAVICON = str(Path(__file__).resolve().parent.parent / "assets" / "favicon.png")
st.set_page_config(
    page_title=desk_config["browser_title"],
    page_icon=_FAVICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_hud_css()
render_terminal_css()
render_sidebar(active_page="pages/07_suppliers.py")
page_command_header(
    desk_config["header_title"],
    desk_config["header_kicker"],
    desk_config["header_flow"],
)

# ── Paths ─────────────────────────────────────────────────────────────────────
_ROOT          = Path(__file__).resolve().parent.parent.parent
_HTML_FILE     = _ROOT / "data" / "suppliers" / "suppliers_dashboard.html"
_SUPPLIERS_DIR = _ROOT / "data" / "suppliers"
_SUPPLIERS_DB  = _SUPPLIERS_DIR / "SUPPLIERS_DB.xlsx"
_SUPPLIERS_PDF = _SUPPLIERS_DIR / "ALL_SUPPLIERS_COMPLETE.pdf"

# ── Action buttons ────────────────────────────────────────────────────────────
col_open, col_xlsx, col_pdf, col_folder, _ = st.columns([1.4, 1, 1, 1, 2])

with col_open:
    if st.button("Abrir no Browser", use_container_width=True,
                 help="Abre suppliers_dashboard.html no browser padrão (macOS)"):
        if _HTML_FILE.exists():
            subprocess.run(["open", str(_HTML_FILE)])
            st.success("Abrindo no browser…")
        else:
            st.error(f"Arquivo não encontrado: {_HTML_FILE}")

with col_xlsx:
    if st.button("SUPPLIERS_DB.xlsx", use_container_width=True,
                 help="Abre planilha de fornecedores"):
        if _SUPPLIERS_DB.exists():
            subprocess.run(["open", str(_SUPPLIERS_DB)])
        else:
            st.warning("SUPPLIERS_DB.xlsx não encontrado.")

with col_pdf:
    if st.button("PDF Completo", use_container_width=True,
                 help="Abre ALL_SUPPLIERS_COMPLETE.pdf"):
        if _SUPPLIERS_PDF.exists():
            subprocess.run(["open", str(_SUPPLIERS_PDF)])
        else:
            st.warning("PDF não encontrado.")

with col_folder:
    if st.button("Abrir Pasta", use_container_width=True,
                 help="Abre data/suppliers/ no Finder"):
        subprocess.run(["open", str(_SUPPLIERS_DIR)])

st.divider()

def _supplier_options(suppliers: list[dict]) -> list[str]:
    return [f"{item['id']} — {item['name']}" for item in suppliers]


def _supplier_from_option(option: str, suppliers: list[dict]) -> dict:
    supplier_id = int(option.split(" — ", 1)[0])
    return next(item for item in suppliers if int(item["id"]) == supplier_id)


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


desk_tab, suppliers_tab, settings_tab = st.tabs(["Desk", "Suppliers", "Tab Settings"])

with desk_tab:
    if not _HTML_FILE.exists():
        rebuild_supplier_dashboard(desk_data)

    html_content = _HTML_FILE.read_text(encoding="utf-8")
    st.components.v1.html(html_content, height=820, scrolling=True)

with suppliers_tab:
    suppliers = desk_data.get("suppliers", [])
    st.caption("Edits here update `data/suppliers/suppliers.json` and rebuild the browser dashboard.")
    mode = st.radio("Action", ["Edit", "Add", "Remove"], horizontal=True, label_visibility="collapsed")

    if mode == "Edit":
        if not suppliers:
            st.info("No suppliers registered.")
        else:
            selected = st.selectbox("Supplier", _supplier_options(suppliers))
            current = _supplier_from_option(selected, suppliers)
            with st.form("edit_supplier_form"):
                c1, c2 = st.columns(2)
                with c1:
                    name = st.text_input("Name", value=current["name"])
                    contact = st.text_input("Contact", value=current.get("contact", ""))
                    phone = st.text_input("Phone", value=current.get("phone", ""))
                    whatsapp = st.text_input("WhatsApp digits", value=current.get("whatsapp", ""))
                    state = st.text_input("State", value=current.get("state", ""))
                with c2:
                    delivery = st.text_input("Delivery note", value=current.get("delivery", ""))
                    color = st.text_input("Card color", value=current.get("color", "#546E7A"))
                    categories = st.text_input("Categories", value=", ".join(current.get("categories", [])))
                    files = st.multiselect(
                        "Related files",
                        options=list(FILE_LINKS),
                        default=[key for key in current.get("files", []) if key in FILE_LINKS],
                    )
                products = st.text_area("Products", value=current.get("products", ""), height=90)
                submitted = st.form_submit_button("Save supplier", type="primary")
            if submitted:
                updated = {
                    **current,
                    "name": name,
                    "contact": contact,
                    "phone": phone,
                    "whatsapp": whatsapp,
                    "state": state,
                    "delivery": delivery,
                    "products": products,
                    "categories": _parse_csv(categories),
                    "color": color,
                    "files": files,
                }
                desk_data["suppliers"] = [
                    updated if int(item["id"]) == int(current["id"]) else item
                    for item in suppliers
                ]
                save_supplier_desk(desk_data)
                rebuild_supplier_dashboard(desk_data)
                st.success("Supplier saved and dashboard rebuilt.")
                st.rerun()

    if mode == "Add":
        with st.form("add_supplier_form"):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Name")
                contact = st.text_input("Contact")
                phone = st.text_input("Phone")
                whatsapp = st.text_input("WhatsApp digits")
                state = st.text_input("State")
            with c2:
                delivery = st.text_input("Delivery note")
                color = st.text_input("Card color", value="#546E7A")
                categories = st.text_input("Categories", placeholder="chaveiro, bolsa")
                files = st.multiselect("Related files", options=list(FILE_LINKS), default=["master"])
            products = st.text_area("Products", height=90)
            submitted = st.form_submit_button("Add supplier", type="primary")
        if submitted:
            if not name.strip():
                st.error("Supplier name is required.")
            else:
                suppliers.append({
                    "id": next_supplier_id(suppliers),
                    "name": name,
                    "contact": contact,
                    "phone": phone,
                    "whatsapp": whatsapp,
                    "state": state,
                    "delivery": delivery,
                    "products": products,
                    "categories": _parse_csv(categories),
                    "color": color,
                    "files": files,
                })
                desk_data["suppliers"] = suppliers
                save_supplier_desk(desk_data)
                rebuild_supplier_dashboard(desk_data)
                st.success("Supplier added and dashboard rebuilt.")
                st.rerun()

    if mode == "Remove":
        if not suppliers:
            st.info("No suppliers registered.")
        else:
            selected = st.selectbox("Supplier to remove", _supplier_options(suppliers))
            current = _supplier_from_option(selected, suppliers)
            st.warning(f"Removing supplier: {current['name']}")
            confirm = st.checkbox("I understand this removes the supplier from the JSON source.")
            if st.button("Remove supplier", type="primary", disabled=not confirm):
                desk_data["suppliers"] = [
                    item for item in suppliers if int(item["id"]) != int(current["id"])
                ]
                save_supplier_desk(desk_data)
                rebuild_supplier_dashboard(desk_data)
                st.success("Supplier removed and dashboard rebuilt.")
                st.rerun()

with settings_tab:
    st.caption("These settings control the page header and sidebar label.")
    with st.form("supplier_tab_settings_form"):
        browser_title = st.text_input("Browser title", value=desk_config["browser_title"])
        header_title = st.text_input("Header title", value=desk_config["header_title"])
        header_kicker = st.text_input("Header kicker", value=desk_config["header_kicker"])
        header_flow = st.text_input("Header flow", value=desk_config["header_flow"])
        c1, c2 = st.columns(2)
        with c1:
            nav_code = st.text_input("Sidebar code", value=desk_config["nav_code"], max_chars=4)
        with c2:
            nav_label = st.text_input("Sidebar label", value=desk_config["nav_label"])
        submitted = st.form_submit_button("Save tab settings", type="primary")
    if submitted:
        desk_data["config"] = {
            "browser_title": browser_title,
            "header_title": header_title,
            "header_kicker": header_kicker,
            "header_flow": header_flow,
            "nav_code": nav_code,
            "nav_label": nav_label,
        }
        save_supplier_desk(desk_data)
        rebuild_supplier_dashboard(desk_data)
        st.success("Tab settings saved. Sidebar label updates on refresh.")
        st.rerun()
