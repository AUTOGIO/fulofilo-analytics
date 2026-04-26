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
from datetime import date, datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.db import get_conn
from app.components.sidebar import render_sidebar, render_page_header
from app.components.hud import inject_hud_css, render_hud_topbar, hud_plotly_layout
from app.utils.inventory_ops import decrement_stock
from app.utils.sales_ops import sync_csv_to_excel_daily_ops

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

    # ── Auto-decrement inventory → parquet + Excel Inventory sheet ─────────────
    inv_result = decrement_stock(product.strip(), quantity)

    # ── Sync daily sales CSV → Excel "Daily Ops" sheet ─────────────────────────
    sync_csv_to_excel_daily_ops()

    return total, inv_result


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
render_page_header()
render_hud_topbar("Operações Diárias", "⚡")

st.markdown(f"**Hoje:** {date.today().strftime('%d/%m/%Y')}")

# ── Quick Product Lookup ───────────────────────────────────────────────────────
st.subheader("🔍 Consulta Rápida de Produto")
conn = get_conn()

try:
    products_df = conn.execute("""
        SELECT sku, full_name, category,
               unit_cost,
               suggested_price AS price, margin_pct
        FROM products ORDER BY full_name
    """).pl().to_pandas()

    search = st.text_input("Buscar produto por nome", placeholder="Ex: necessaire, chaveiro, carteira...")
    if search:
        mask = (
            products_df["full_name"].str.lower().str.contains(search.lower()) |
            products_df["sku"].str.lower().str.contains(search.lower(), na=False)
        )
        result = products_df[mask].copy()
        if not result.empty:
            result.columns = ["Slug", "Produto", "Categoria", "Custo Unit. (R$)", "Preço (R$)", "Margem (%)"]
            result["Custo Unit. (R$)"]    = result["Custo Unit. (R$)"].apply(lambda x: f"R$ {x:.2f}" if x else "—")
            result["Preço (R$)"]          = result["Preço (R$)"].apply(lambda x: f"R$ {x:.2f}" if x else "—")
            result["Margem (%)"]          = result["Margem (%)"].apply(lambda x: f"{x:.1f}%" if x else "—")
            st.dataframe(result, use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum produto encontrado.")
except Exception:
    st.info("Execute `etl/build_catalog.py` para habilitar a consulta de produtos.")

st.divider()

# ── Daily Sales Entry Form ─────────────────────────────────────────────────────
st.subheader("📝 Registro de Vendas do Dia")
st.markdown("Cada venda registrada aqui é **salva imediatamente** no CSV e no Parquet.")

# Load product list for dropdown
@st.cache_data
def load_product_options():
    try:
        prod = pl.read_parquet(PROJECT_ROOT / "data" / "parquet" / "products.parquet")
        df = prod.select(["sku","full_name","category","price"]).sort(["category","full_name"]).to_pandas()
        # Build options: "Categoria — Nome" → (full_name, price)
        options = {}
        for _, r in df.iterrows():
            label = f"{r['category']} — {r['full_name'].replace(r['category'] + ' — ', '').replace(r['category'] + ' — ', '')}"
            options[label] = {"name": r["full_name"], "price": float(r["price"])}
        return options
    except Exception:
        return {}

product_options = load_product_options()
product_labels  = list(product_options.keys())

# Product selector (outside form for price auto-fill)
selected_label = st.selectbox(
    "🛍️ Produto",
    options=product_labels,
    index=0 if product_labels else None,
    placeholder="Selecione um produto...",
)
selected_product = product_options.get(selected_label, {})
default_price    = selected_product.get("price", 15.0)
product_name     = selected_product.get("name", "")

with st.form("daily_sale_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        sale_date  = st.date_input("Data", value=date.today())
        quantity   = st.number_input("Quantidade", min_value=1, value=1, step=1)
    with col2:
        unit_price = st.number_input("Preço Unitário (R$)", min_value=0.01,
                                     value=default_price, step=0.50)
        payment    = st.selectbox(
            "Forma de Pagamento",
            ["Dinheiro", "Pix", "Débito", "Crédito", "Crédito Parcelado"],
        )
    with col3:
        notes = st.text_input("Observações", placeholder="Opcional")
        st.markdown(f"<br><span style='color:#00D4FF;font-size:0.85rem;'>💰 Preço tabela: <b>R$ {default_price:.2f}</b></span>", unsafe_allow_html=True)

    submitted = st.form_submit_button("✅ Registrar Venda", use_container_width=True)

if submitted:
    if not product_name:
        st.error("❌ Selecione um produto.")
    else:
        total, inv_result = append_sale(sale_date, product_name, quantity, unit_price, payment, notes)
        st.success(
            f"✅ **{product_name}** × {quantity} = **R$ {total:.2f}** ({payment}) — "
            f"salvo em CSV e Parquet."
        )
        if inv_result:
            delta = inv_result["old_stock"] - inv_result["new_stock"]
            st.info(
                f"📦 Estoque atualizado: **{inv_result['product']}** "
                f"{inv_result['old_stock']} → **{inv_result['new_stock']}** "
                f"(-{delta} un.) · Excel sincronizado ✔"
            )
        else:
            st.warning("⚠️ Produto não encontrado no estoque — ajuste manual se necessário.")
        st.rerun()

st.divider()

# ── Daily Summary ─────────────────────────────────────────────────────────────
hdr_col1, hdr_col2 = st.columns([4, 1])
with hdr_col1:
    st.subheader("📊 Histórico de Vendas")
with hdr_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Sync → Excel", use_container_width=True, type="primary"):
        path = sync_csv_to_excel_daily_ops()
        if path:
            from pathlib import Path as _P
            st.success(f"✅ `{_P(path).name}` atualizado!")
        else:
            st.error("❌ Excel não encontrado.")
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

    # ── Date range selector ────────────────────────────────────────────────────
    min_date = history["Date"].min().date()
    max_date = history["Date"].max().date()
    default_start = max(min_date, max_date - timedelta(days=29))

    col_range_a, col_range_b, col_range_c = st.columns([2, 2, 1])
    with col_range_a:
        range_start = st.date_input("📅 De", value=default_start,
                                    min_value=min_date, max_value=max_date,
                                    key="range_start")
    with col_range_b:
        range_end = st.date_input("📅 Até", value=max_date,
                                  min_value=min_date, max_value=max_date,
                                  key="range_end")
    with col_range_c:
        st.markdown("<br>", unsafe_allow_html=True)
        quick_30 = st.button("⚡ Últimos 30d")
        if quick_30:
            range_start = max(min_date, max_date - timedelta(days=29))
            range_end   = max_date

    # ── Apply range filter ─────────────────────────────────────────────────────
    mask = (
        (history["Date"].dt.date >= range_start) &
        (history["Date"].dt.date <= range_end)
    )
    filtered_history = history[mask]

    n_days = (range_end - range_start).days + 1
    avg_daily = filtered_history["Total"].sum() / n_days if n_days else 0

    f1, f2, f3, f4 = st.columns(4)
    f1.metric("📦 Transações",      f"{len(filtered_history)}")
    f2.metric("💰 Receita Período", f"R$ {filtered_history['Total'].sum():,.2f}")
    f3.metric("📊 Média Diária",    f"R$ {avg_daily:,.2f}")
    f4.metric("🗓️ Dias",            f"{n_days}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Revenue bar chart with range ───────────────────────────────────────────
    daily_agg = (
        filtered_history
        .groupby(filtered_history["Date"].dt.strftime("%Y-%m-%d"))["Total"]
        .sum()
        .reset_index()
        .rename(columns={"Date": "Data", "Total": "Receita (R$)"})
        .sort_values("Data")
    )

    chart_title = (
        f"Receita Diária — {range_start.strftime('%d/%m/%Y')} a {range_end.strftime('%d/%m/%Y')}"
    )
    fig = px.bar(
        daily_agg, x="Data", y="Receita (R$)",
        title=chart_title,
        color_discrete_sequence=["#00D4FF"],
    )
    fig.update_traces(marker_line_width=0)
    fig.add_hline(y=avg_daily, line_dash="dot", line_color="#FFD700", opacity=0.7,
                  annotation_text=f"Média R$ {avg_daily:,.0f}",
                  annotation_font_color="#FFD700",
                  annotation_position="top left")
    hud_plotly_layout(fig, height=380)
    st.plotly_chart(fig, use_container_width=True)

    # ── Payment method breakdown ───────────────────────────────────────────────
    if not filtered_history.empty:
        pay_agg = (
            filtered_history.groupby("Payment_Method")["Total"]
            .sum()
            .reset_index()
            .rename(columns={"Payment_Method": "Pagamento", "Total": "Receita (R$)"})
            .sort_values("Receita (R$)", ascending=False)
        )

        col_pie, col_tbl = st.columns([1, 1])
        with col_pie:
            fig_pay = px.pie(
                pay_agg, values="Receita (R$)", names="Pagamento",
                title="Receita por Forma de Pagamento",
                color_discrete_sequence=["#00D4FF","#00FF88","#FFD700","#FF4455","#A78BFA"],
            )
            fig_pay.update_traces(
                textfont_color="#E2E8F0",
                marker=dict(line=dict(color="#080C18", width=2)),
            )
            hud_plotly_layout(fig_pay, height=320)
            st.plotly_chart(fig_pay, use_container_width=True)

        with col_tbl:
            st.markdown("**Resumo por Pagamento**")
            pay_agg["Receita (R$)"] = pay_agg["Receita (R$)"].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(pay_agg, use_container_width=True, hide_index=True)

    with st.expander("📋 Todas as vendas no período", expanded=False):
        show = filtered_history.sort_values("Date", ascending=False).copy()
        show["Date"]       = show["Date"].dt.strftime("%d/%m/%Y")
        show["Unit_Price"] = show["Unit_Price"].apply(lambda x: f"R$ {x:.2f}")
        show["Total"]      = show["Total"].apply(lambda x: f"R$ {x:.2f}")
        show.columns       = ["Data", "Produto", "Qtd", "Preço Unit.", "Total", "Pagamento", "Fonte"]
        st.dataframe(show, use_container_width=True, hide_index=True)

# ── Delete a Sale ──────────────────────────────────────────────────────────────
st.divider()
with st.expander("🗑️ Excluir Venda", expanded=False):
    st.warning("⚠️ Esta ação é irreversível. A venda será removida do CSV, Parquet e Excel.")

    del_history = load_sales_history()
    if del_history.empty:
        st.info("Nenhuma venda registrada ainda.")
    else:
        del_df = del_history.reset_index(drop=True).copy()

        # ── Optional date filter to narrow down the list ───────────────────
        min_d = del_df["Date"].min().date()
        max_d = del_df["Date"].max().date()
        dc1, dc2 = st.columns(2)
        with dc1:
            del_from = st.date_input("📅 A partir de", value=max_d - timedelta(days=6),
                                     min_value=min_d, max_value=max_d, key="del_from")
        with dc2:
            del_to   = st.date_input("📅 Até", value=max_d,
                                     min_value=min_d, max_value=max_d, key="del_to")

        mask_del = (del_df["Date"].dt.date >= del_from) & (del_df["Date"].dt.date <= del_to)
        subset   = del_df[mask_del].copy()

        if subset.empty:
            st.info("Nenhuma venda no período selecionado.")
        else:
            subset["_label"] = subset.apply(
                lambda r: (
                    f"{r['Date'].strftime('%d/%m/%Y')}  |  "
                    f"{r['Product']}  |  "
                    f"Qtd {int(r['Quantity'])}  |  "
                    f"R$ {float(r['Total']):.2f}  |  "
                    f"{r['Payment_Method']}"
                ),
                axis=1,
            )

            selected_label = st.selectbox(
                "Selecionar venda para excluir:",
                subset["_label"].tolist(),
                key="delete_sale_select",
            )

            # Map label → original DataFrame index
            orig_idx = subset[subset["_label"] == selected_label].index[0]
            row      = del_df.loc[orig_idx]

            st.markdown(
                f"**Venda selecionada:** `{row['Product']}` — "
                f"**{int(row['Quantity'])} un × R$ {float(row['Unit_Price']):.2f}** "
                f"= **R$ {float(row['Total']):.2f}** ({row['Payment_Method']}) "
                f"em {row['Date'].strftime('%d/%m/%Y')}"
            )

            confirm_cb = st.checkbox("✅ Confirmar exclusão desta venda", key="confirm_delete_cb")
            if st.button("🗑️ Excluir venda", type="primary",
                         disabled=not confirm_cb, use_container_width=False):
                new_df = del_df.drop(index=orig_idx).reset_index(drop=True)
                # Re-format Date as string for CSV consistency
                new_df["Date"] = new_df["Date"].dt.strftime("%Y-%m-%d")
                new_df.to_csv(CSV_PATH, index=False)
                _rebuild_parquet()
                sync_csv_to_excel_daily_ops()
                st.success(
                    f"✅ Venda excluída: **{row['Product']}** "
                    f"em {row['Date'].strftime('%d/%m/%Y')} — "
                    f"CSV, Parquet e Excel atualizados."
                )
                st.cache_data.clear()
                st.rerun()

