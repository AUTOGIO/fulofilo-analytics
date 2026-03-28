"""
FulôFiló — Operações Diárias (HUD Edition)
==========================================
Daily sales tracker with persistent CSV + Parquet write.
Each form submission is immediately written to disk and the parquet is regenerated.
"""

import csv
import streamlit as st
import plotly.express as px
import pandas as pd
import polars as pl
import sys
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.db import get_conn
from app.components.sidebar import render_sidebar
from app.components.hud import inject_hud_css, render_hud_topbar, hud_plotly_layout

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH     = PROJECT_ROOT / "data" / "raw" / "daily_sales_TEMPLATE.csv"
PARQUET_PATH = PROJECT_ROOT / "data" / "parquet" / "daily_sales.parquet"
CSV_COLUMNS  = ["Date", "Product", "Quantity", "Unit_Price", "Total", "Payment_Method", "Source"]

# ── Helpers ───────────────────────────────────────────────────────────────────
def _ensure_csv_header():
    if not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()


def append_sale(sale_date, product, quantity, unit_price, payment, notes=""):
    _ensure_csv_header()
    total = round(quantity * unit_price, 2)
    row = {
        "Date":           sale_date.strftime("%Y-%m-%d"),
        "Product":        product.strip(),
        "Quantity":       quantity,
        "Unit_Price":     round(unit_price, 2),
        "Total":          total,
        "Payment_Method": payment,
        "Source":         "manual",
    }
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writerow(row)
    _rebuild_parquet()
    return total


def _rebuild_parquet():
    try:
        df = pl.read_csv(
            CSV_PATH,
            schema_overrides={"Quantity": pl.Int64, "Unit_Price": pl.Float64, "Total": pl.Float64},
            try_parse_dates=True,
        )
        PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(PARQUET_PATH)
    except Exception as e:
        st.warning(f"⚠️ Parquet não atualizado: {e}")


def load_sales_history() -> pd.DataFrame:
    _ensure_csv_header()
    return pd.read_csv(CSV_PATH, parse_dates=["Date"])


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Operações Diárias — FulôFiló", page_icon="⚡", layout="wide")
inject_hud_css()
render_sidebar()
render_hud_topbar("Operações Diárias", "⚡")

st.markdown(f"**Hoje:** {date.today().strftime('%d/%m/%Y')}")

# ── Quick Product Lookup ───────────────────────────────────────────────────────
st.subheader("🔍 Consulta Rápida de Produto")
conn = get_conn()

try:
    products_df = conn.execute("""
        SELECT sku, full_name, category, unit_cost, suggested_price, margin_pct
        FROM products ORDER BY full_name
    """).pl().to_pandas()

    search = st.text_input("Buscar produto por nome ou SKU", placeholder="Ex: canga, 00007, chaveiro...")
    if search:
        mask = (
            products_df["full_name"].str.lower().str.contains(search.lower()) |
            products_df["sku"].str.contains(search, na=False)
        )
        result = products_df[mask].copy()
        if not result.empty:
            result.columns = ["SKU", "Produto", "Categoria", "Custo (R$)", "Preço Sugerido (R$)", "Margem (%)"]
            result["Custo (R$)"]          = result["Custo (R$)"].apply(lambda x: f"R$ {x:.2f}")
            result["Preço Sugerido (R$)"] = result["Preço Sugerido (R$)"].apply(lambda x: f"R$ {x:.2f}")
            result["Margem (%)"]          = result["Margem (%)"].apply(lambda x: f"{x:.1f}%")
            st.dataframe(result, use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum produto encontrado.")
except Exception:
    st.info("Execute `etl/build_catalog.py` para habilitar a consulta de produtos.")

st.divider()

# ── Daily Sales Entry Form ─────────────────────────────────────────────────────
st.subheader("📝 Registro de Vendas do Dia")
st.markdown("Cada venda registrada aqui é **salva imediatamente** no CSV e no Parquet.")

with st.form("daily_sale_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        sale_date    = st.date_input("Data", value=date.today())
        product_name = st.text_input("Produto", placeholder="Ex: Nécessaire Stylo")
    with col2:
        quantity   = st.number_input("Quantidade", min_value=1, value=1, step=1)
        unit_price = st.number_input("Preço Unitário (R$)", min_value=0.01, value=15.00, step=0.50)
    with col3:
        payment = st.selectbox(
            "Forma de Pagamento",
            ["Dinheiro", "Pix", "Débito", "Crédito", "Crédito Parcelado"],
        )
        notes = st.text_input("Observações", placeholder="Opcional")

    submitted = st.form_submit_button("✅ Registrar Venda", use_container_width=True)

if submitted:
    if not product_name.strip():
        st.error("❌ Informe o nome do produto.")
    else:
        total = append_sale(sale_date, product_name, quantity, unit_price, payment, notes)
        st.success(
            f"✅ **{product_name}** × {quantity} = **R$ {total:.2f}** ({payment}) — "
            f"salvo em `daily_sales_TEMPLATE.csv` e Parquet atualizado."
        )
        st.rerun()

st.divider()

# ── Daily Summary ─────────────────────────────────────────────────────────────
st.subheader("📊 Resumo do Dia (Histórico)")
history = load_sales_history()

if history.empty:
    st.info("Nenhuma venda registrada ainda. Use o formulário acima para começar.")
else:
    today_str = date.today().strftime("%Y-%m-%d")
    today_df  = history[history["Date"].dt.strftime("%Y-%m-%d") == today_str]

    k1, k2, k3 = st.columns(3)
    k1.metric("Vendas Hoje",       f"{len(today_df)}")
    k2.metric("Receita Hoje",      f"R$ {today_df['Total'].sum():.2f}")
    k3.metric("Ticket Médio Hoje", f"R$ {today_df['Total'].mean():.2f}" if len(today_df) else "R$ 0,00")

    st.divider()

    daily_agg = (
        history.groupby(history["Date"].dt.strftime("%Y-%m-%d"))["Total"]
        .sum()
        .reset_index()
        .rename(columns={"Date": "Data", "Total": "Receita (R$)"})
        .sort_values("Data")
        .tail(30)
    )
    fig = px.bar(
        daily_agg, x="Data", y="Receita (R$)",
        title="Receita Diária — Últimos 30 dias",
        color_discrete_sequence=["#00D4FF"],
    )
    fig.update_traces(marker_line_width=0)
    hud_plotly_layout(fig, height=360)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 Todas as vendas registradas", expanded=False):
        show = history.sort_values("Date", ascending=False).copy()
        show["Date"]       = show["Date"].dt.strftime("%d/%m/%Y")
        show["Unit_Price"] = show["Unit_Price"].apply(lambda x: f"R$ {x:.2f}")
        show["Total"]      = show["Total"].apply(lambda x: f"R$ {x:.2f}")
        show.columns       = ["Data", "Produto", "Qtd", "Preço Unit.", "Total", "Pagamento", "Fonte"]
        st.dataframe(show, use_container_width=True, hide_index=True)
