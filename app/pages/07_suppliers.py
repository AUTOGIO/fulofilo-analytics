"""
FulôFiló - Supplier Intelligence Terminal
=========================================
Native Streamlit supplier desk. This page intentionally does not embed the
legacy suppliers_dashboard.html because all production tabs must share the
institutional terminal design system.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.components.hud import HUD, inject_hud_css
from app.components.sidebar import render_page_header, render_sidebar
from app.components.terminal import kpi_grid, page_command_header, panel, render_terminal_css


_FAVICON = str(Path(__file__).resolve().parent.parent / "assets" / "favicon.png")
st.set_page_config(
    page_title="Supplier Intelligence - FulôFiló",
    page_icon=_FAVICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_hud_css()
render_terminal_css()
render_sidebar(active_page="pages/07_suppliers.py")
render_page_header()
page_command_header(
    "Supplier Intelligence",
    "AI / sourcing desk",
    "supplier workbook -> sourcing control -> restock and margin decisions",
)

_ROOT = Path(__file__).resolve().parent.parent.parent
_SUPPLIERS_DIR = _ROOT / "data" / "suppliers"
_SUPPLIERS_DB = _SUPPLIERS_DIR / "SUPPLIERS_DB.xlsx"
_SUPPLIERS_PDF = _SUPPLIERS_DIR / "ALL_SUPPLIERS_COMPLETE.pdf"
_SUPPLIERS_MD = _SUPPLIERS_DIR / "ALL_SUPPLIERS_COMPLETE.md"


@st.cache_data(show_spinner=False)
def _load_supplier_data(path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load supplier workbook sheets whose first row is a dashboard link row."""
    workbook = Path(path)
    if not workbook.exists():
        return pd.DataFrame(), pd.DataFrame()

    full = pd.read_excel(workbook, sheet_name="📋 Full Data", header=1)
    quick = pd.read_excel(workbook, sheet_name="📞 Quick Contact", header=1)

    full = full.dropna(how="all").copy()
    quick = quick.dropna(how="all").copy()
    full.columns = [str(col).strip() for col in full.columns]
    quick.columns = [str(col).strip() for col in quick.columns]
    full = full.rename(columns={"#": "ID"})
    quick = quick.rename(columns={"#": "ID", "Supplier / Contact": "Company"})

    for frame in (full, quick):
        for column in frame.columns:
            frame[column] = frame[column].fillna("—").astype(str).str.strip()

    return full, quick


def _unique_product_terms(df: pd.DataFrame) -> set[str]:
    if "Products" not in df.columns:
        return set()
    terms: set[str] = set()
    for products in df["Products"].dropna().astype(str):
        for term in products.replace(";", ",").split(","):
            cleaned = term.strip()
            if cleaned and cleaned != "—":
                terms.add(cleaned.lower())
    return terms


def _artifact_state(path: Path) -> str:
    return "READY" if path.exists() else "MISSING"


full_df, quick_df = _load_supplier_data(str(_SUPPLIERS_DB))

if full_df.empty:
    panel(
        "Supplier Desk Offline",
        "artifact missing",
        (
            f"<div style='color:{HUD['text_dim']};font-size:0.78rem;'>"
            f"Expected workbook: {_SUPPLIERS_DB}</div>"
        ),
    )
    st.stop()

states = sorted([state for state in full_df.get("State", pd.Series(dtype=str)).unique() if state != "—"])
product_terms = _unique_product_terms(full_df)
artifact_count = sum(path.exists() for path in [_SUPPLIERS_DB, _SUPPLIERS_PDF, _SUPPLIERS_MD])

st.markdown(
    kpi_grid(
        [
            {
                "label": "Supplier Coverage",
                "value": f"{len(full_df)}",
                "delta": "active sourcing records",
                "color": HUD["cyan"],
            },
            {
                "label": "Geographic Reach",
                "value": f"{len(states)}",
                "delta": ", ".join(states) if states else "state field pending",
                "color": HUD["green"],
            },
            {
                "label": "Product Signals",
                "value": f"{len(product_terms)}",
                "delta": "parsed category / SKU opportunities",
                "color": HUD["gold"],
            },
            {
                "label": "Artifacts",
                "value": f"{artifact_count}/3",
                "delta": "xlsx / pdf / markdown",
                "color": HUD["green"] if artifact_count == 3 else HUD["amber"],
            },
        ]
    ),
    unsafe_allow_html=True,
)

st.markdown('<div class="ff-section-label">Supplier Command Window</div>', unsafe_allow_html=True)
a1, a2, a3 = st.columns([1, 1, 2])
with a1:
    if _SUPPLIERS_DB.exists():
        st.download_button(
            "DB XLSX",
            data=_SUPPLIERS_DB.read_bytes(),
            file_name=_SUPPLIERS_DB.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.button("DB XLSX Missing", disabled=True, use_container_width=True)
with a2:
    if _SUPPLIERS_PDF.exists():
        st.download_button(
            "Supplier PDF",
            data=_SUPPLIERS_PDF.read_bytes(),
            file_name=_SUPPLIERS_PDF.name,
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.button("PDF Missing", disabled=True, use_container_width=True)
with a3:
    st.caption(
        "Supplier artifacts remain generated intelligence files under "
        "`data/suppliers`; operational source discipline stays Excel-first."
    )

st.markdown('<div class="ff-section-label">Generated Supplier Artifacts</div>', unsafe_allow_html=True)
asset_df = pd.DataFrame(
    [
        {
            "Artifact": path.name,
            "State": _artifact_state(path),
            "Path": str(path),
        }
        for path in [_SUPPLIERS_DB, _SUPPLIERS_PDF, _SUPPLIERS_MD]
    ]
)
st.dataframe(asset_df, use_container_width=True, hide_index=True, height=150)

st.markdown('<div class="ff-section-label">Supplier Surveillance Grid</div>', unsafe_allow_html=True)
f1, f2, f3 = st.columns([2, 1, 1])
with f1:
    search = st.text_input("Command Search", placeholder="supplier, product, city, contact...")
with f2:
    state_filter = st.multiselect("State", states, default=states)
with f3:
    delivery_filter = st.selectbox("Delivery Visibility", ["All", "Known only", "Pending only"])

view = full_df.copy()
if state_filter and "State" in view.columns:
    view = view[view["State"].isin(state_filter)]
if delivery_filter == "Known only" and "Delivery" in view.columns:
    view = view[view["Delivery"] != "—"]
elif delivery_filter == "Pending only" and "Delivery" in view.columns:
    view = view[view["Delivery"] == "—"]
if search:
    haystack = view.astype(str).agg(" ".join, axis=1).str.lower()
    view = view[haystack.str.contains(search.lower(), na=False)]

display_columns = [
    column
    for column in ["Company", "Contact", "Phone", "City", "State", "Delivery", "Products"]
    if column in view.columns
]

st.caption(f"{len(view)} supplier records in current surveillance view.")
st.dataframe(
    view[display_columns],
    use_container_width=True,
    hide_index=True,
    height=360,
)

st.markdown('<div class="ff-section-label">Sourcing Intelligence</div>', unsafe_allow_html=True)
left, right = st.columns([1.15, 0.85])
with left:
    if "State" in full_df.columns:
        state_counts = (
            full_df.groupby("State", dropna=False)["Company"]
            .count()
            .reset_index()
            .rename(columns={"Company": "Suppliers"})
            .sort_values("Suppliers", ascending=False)
        )
        st.dataframe(state_counts, use_container_width=True, hide_index=True, height=220)

with right:
    chips = "".join(
        f'<span class="ff-chip">{term}</span>'
        for term in sorted(product_terms)[:24]
    )
    panel(
        "Detected Product Signals",
        "first 24 parsed terms",
        f'<div class="ff-chip-row">{chips}</div>',
    )

quick_columns = [
    column
    for column in ["Company", "Phone / WhatsApp", "State", "Delivery", "Products"]
    if column in quick_df.columns
]
st.markdown('<div class="ff-section-label">Quick Contact Desk</div>', unsafe_allow_html=True)
st.dataframe(quick_df[quick_columns], use_container_width=True, hide_index=True, height=300)
