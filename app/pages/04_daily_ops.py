"""
FulôFiló — Operações Diárias (HUD Edition)
==========================================
Manual DailySales entry plus read-only sales history over the canonical Excel-first sync outputs.
"""

import streamlit as st
import plotly.express as px
import pandas as pd
import polars as pl
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.db import get_conn
from app.components.sidebar import render_sidebar, render_page_header
from app.components.hud import inject_hud_css, hud_plotly_layout
from app.components.terminal import page_command_header, render_terminal_css
from app.utils.sales_ops import append_sale_to_excel
from app.utils.source_health import render_source_health_warning

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PARQUET_PATH = PROJECT_ROOT / "data" / "parquet" / "daily_sales.parquet"
def load_sales_history() -> pd.DataFrame:
    if not PARQUET_PATH.exists():
        return pd.DataFrame(
            columns=["Date", "Product", "Quantity", "Unit_Price", "Total", "Payment_Method", "Source"]
        )
    df = pl.read_parquet(PARQUET_PATH).to_pandas()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Operações Diárias — FulôFiló", page_icon="⚡", layout="wide")
inject_hud_css()
render_terminal_css()
render_sidebar()
render_page_header()
page_command_header(
    "Daily Operations",
    "DO / sales capture",
    "DailySales canonical write -> sync pipeline -> operational read models",
    status="CONTROLLED WRITE",
)
render_source_health_warning()

st.caption(f"Trading day: {date.today().strftime('%d/%m/%Y')} · manual writes are restricted to DailySales.")

# ── Manual sales entry ────────────────────────────────────────────────────────
st.subheader("📝 Registrar Venda Manual")
st.caption("Somente `DailySales` deve ser atualizado manualmente. O restante do fluxo roda pela rotina automática.")

conn = get_conn()
products_df = pd.DataFrame(columns=["sku", "full_name", "category", "unit_cost", "price", "margin_pct"])

try:
    products_df = conn.execute("""
        SELECT sku, full_name, category,
               unit_cost,
               suggested_price AS price, margin_pct
        FROM products ORDER BY full_name
    """).pl().to_pandas()
finally:
    conn.close()

if products_df.empty:
    st.info("Execute `bash scripts/sync_excel.sh` para habilitar o lançamento manual de vendas.")
else:
    product_options = [
        f"{row.full_name} ({row.sku})"
        for row in products_df.itertuples(index=False)
    ]
    option_map = dict(zip(product_options, products_df.to_dict(orient="records")))

    with st.form("manual_sale_form", clear_on_submit=False):
        fc1, fc2 = st.columns([3, 1])
        with fc1:
            selected_label = st.selectbox("Produto", product_options)
        with fc2:
            sale_date = st.date_input("Data", value=date.today())

        selected_product = option_map[selected_label]
        default_price = float(selected_product.get("price") or 0.0)

        fc3, fc4, fc5, fc6 = st.columns([1, 1, 1, 1])
        with fc3:
            quantity = st.number_input("Quantidade", min_value=1, value=1, step=1)
        with fc4:
            unit_price = st.number_input("Preço unitário", min_value=0.0, value=default_price, step=1.0, format="%.2f")
        with fc5:
            payment_method = st.selectbox("Pagamento", ["Pix", "Cartão", "Dinheiro", "Transferência", "Outro"])
        with fc6:
            st.markdown("<br>", unsafe_allow_html=True)
            total = float(quantity) * float(unit_price)
            st.metric("Total", f"R$ {total:.2f}")

        submitted_sale = st.form_submit_button("💾 Salvar venda", use_container_width=True)

    if submitted_sale:
        try:
            result = append_sale_to_excel(
                sale_date=sale_date,
                sku=str(selected_product["sku"]),
                product=str(selected_product["full_name"]),
                quantity=int(quantity),
                unit_price=float(unit_price),
                payment_method=str(payment_method),
                source="manual-app",
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"Falha ao gravar venda no Excel master: {exc}")
        else:
            st.success(
                f"Venda salva: {result.product} | {result.quantity} un. | "
                f"R$ {result.total:.2f}. Sync executado automaticamente."
            )
            st.cache_data.clear()
            st.rerun()

st.divider()

# ── Quick Product Lookup ───────────────────────────────────────────────────────
st.subheader("🔍 Consulta Rápida de Produto")
try:
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
    st.info("Execute `bash scripts/sync_excel.sh` para habilitar a consulta de produtos.")

st.divider()

# ── Daily Summary ─────────────────────────────────────────────────────────────
hdr_col1, hdr_col2 = st.columns([4, 1])
with hdr_col1:
    st.subheader("📊 Histórico de Vendas")
with hdr_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.button("🔄 Sync já aplicado", use_container_width=True, type="primary", disabled=True)
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

st.divider()
with st.expander("🗑️ Excluir Venda", expanded=False):
    st.warning(DISABLED_WRITEBACK_MSG)
