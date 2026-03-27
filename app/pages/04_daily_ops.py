"""
FulôFiló — Operações Diárias
==============================
Daily sales tracker, cashflow summary, and quick product lookup.
Designed for use at the POS during store hours.
"""

import streamlit as st
import plotly.express as px
import pandas as pd
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.db import get_conn

st.set_page_config(page_title="Operações Diárias — FulôFiló", page_icon="⚡", layout="wide")
st.title("⚡ Operações Diárias")
st.markdown(f"**Hoje:** {date.today().strftime('%d/%m/%Y')}")

# ── Quick Product Lookup ───────────────────────────────────────────────────────
st.subheader("🔍 Consulta Rápida de Produto")
conn = get_conn()

try:
    products_df = conn.execute("""
        SELECT sku, full_name, category, unit_cost, suggested_price, margin_pct
        FROM products
        ORDER BY full_name
    """).pl().to_pandas()

    search = st.text_input("Buscar produto por nome ou SKU", placeholder="Ex: canga, 00007, chaveiro...")
    if search:
        mask = (
            products_df["full_name"].str.lower().str.contains(search.lower()) |
            products_df["sku"].str.contains(search)
        )
        result = products_df[mask]
        if not result.empty:
            result.columns = ["SKU", "Produto", "Categoria", "Custo (R$)", "Preço Sugerido (R$)", "Margem (%)"]
            result["Custo (R$)"] = result["Custo (R$)"].apply(lambda x: f"R$ {x:.2f}")
            result["Preço Sugerido (R$)"] = result["Preço Sugerido (R$)"].apply(lambda x: f"R$ {x:.2f}")
            result["Margem (%)"] = result["Margem (%)"].apply(lambda x: f"{x:.1f}%")
            st.dataframe(result, width="stretch", hide_index=True)
        else:
            st.warning("Nenhum produto encontrado.")
except Exception:
    st.info("Execute `etl/build_catalog.py` para habilitar a consulta de produtos.")

st.divider()

# ── Daily Sales Entry ─────────────────────────────────────────────────────────
st.subheader("📝 Registro de Vendas do Dia")
st.markdown("Use este formulário para registrar vendas manualmente enquanto aguarda integração com Eleve Vendas.")

with st.form("daily_sale_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        sale_date = st.date_input("Data", value=date.today())
        product_name = st.text_input("Produto", placeholder="Ex: Nécessaire Stylo")
    with col2:
        quantity = st.number_input("Quantidade", min_value=1, value=1)
        unit_price = st.number_input("Preço Unitário (R$)", min_value=0.01, value=15.00, step=0.50)
    with col3:
        payment = st.selectbox("Forma de Pagamento", ["Dinheiro", "Pix", "Débito", "Crédito", "Crédito Parcelado"])
        notes = st.text_input("Observações", placeholder="Opcional")
    
    submitted = st.form_submit_button("✅ Registrar Venda", width="stretch")
    if submitted:
        total = quantity * unit_price
        st.success(f"✅ Venda registrada: **{product_name}** × {quantity} = **R$ {total:.2f}** ({payment})")
        st.info("💡 Para persistir os dados, integre com `data/raw/daily_sales_TEMPLATE.csv` e execute o ETL.")

st.divider()

# ── Daily Summary ─────────────────────────────────────────────────────────────
st.subheader("📊 Resumo do Dia (Histórico)")

try:
    daily_df = conn.execute("""
        SELECT Date, SUM(Total) AS total_day, COUNT(*) AS transactions
        FROM sales
        GROUP BY Date
        ORDER BY Date DESC
        LIMIT 30
    """).pl().to_pandas()
    
    if not daily_df.empty:
        fig = px.bar(
            daily_df,
            x="Date", y="total_day",
            labels={"Date": "Data", "total_day": "Receita (R$)"},
            title="Receita Diária — Últimos 30 dias",
            color_discrete_sequence=["#2D6A4F"],
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Nenhuma venda diária registrada ainda. Preencha `daily_sales_TEMPLATE.csv`.")
except Exception:
    st.info("Dados de vendas diárias não disponíveis. Preencha `data/raw/daily_sales_TEMPLATE.csv`.")
