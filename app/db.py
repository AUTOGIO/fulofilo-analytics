"""
FulôFiló — DuckDB Engine
=========================
Parquet schema (from etl/ingest.py):

  products:    sku, full_name, category, unit_cost, suggested_price,
               min_stock, reorder_qty, unit_profit, margin_pct,
               qty_sold, revenue, profit, cum_pct, abc_class

  inventory:   sku, product, category, current_stock, min_stock, reorder_qty

  daily_sales: Date, Product, Quantity, Unit_Price, Total,
               Payment_Method, Source

  cashflow:    Date, Type, Category, Description, Amount, Payment_Method
"""

import duckdb
from pathlib import Path
import polars as pl

BASE     = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data" / "parquet"
DB_PATH  = BASE / "data" / "fulofilo.duckdb"


def get_data_mtime() -> str:
    """Return a string fingerprint of the parquet directory's latest mtime."""
    mtimes = [p.stat().st_mtime for p in DATA_DIR.glob("*.parquet") if p.exists()]
    return str(round(max(mtimes), 3)) if mtimes else "0"


def get_conn():
    """Initialize DuckDB connection and register Parquet files as views."""
    import os
    is_cloud = bool(
        os.environ.get("STREAMLIT_SHARING_MODE") or
        os.environ.get("IS_STREAMLIT_CLOUD")
    )

    conn = duckdb.connect(str(DB_PATH))

    if is_cloud:
        conn.execute("SET threads = 2")
        conn.execute("SET memory_limit = '512MB'")
    else:
        conn.execute("SET threads = 8")
        conn.execute("SET memory_limit = '8GB'")
    conn.execute("SET enable_progress_bar = false")
    conn.execute("SET temp_directory = '/tmp/duckdb_fulofilo'")

    for name, fname in [
        ("products",   "products.parquet"),
        ("inventory",  "inventory.parquet"),
        ("sales",      "daily_sales.parquet"),
        ("cashflow",   "cashflow.parquet"),
    ]:
        p = DATA_DIR / fname
        if p.exists():
            conn.execute(
                f"CREATE OR REPLACE VIEW {name} AS "
                f"SELECT * FROM read_parquet('{p}');"
            )

    return conn


# ── Queries ────────────────────────────────────────────────────────────────────

def get_summary_kpis(conn, period: str = "ALL"):
    """High-level KPIs: receita, unidades, lucro, ticket médio."""
    try:
        return conn.execute("""
            SELECT
                SUM(revenue)                                          AS receita,
                SUM(qty_sold)                                         AS quantidade,
                SUM(profit)                                           AS lucro,
                ROUND(SUM(revenue) / NULLIF(SUM(qty_sold), 0), 2)    AS ticket_medio
            FROM products
        """).fetchone()
    except Exception:
        return (0, 0, 0, 0)


def get_abc_analysis(conn, period: str = "ALL"):
    """ABC data ordered by revenue descending."""
    try:
        return conn.execute("""
            SELECT
                full_name,
                category,
                revenue,
                qty_sold,
                profit,
                abc_class,
                cum_pct,
                margin_pct
            FROM products
            ORDER BY revenue DESC
        """).pl()
    except Exception:
        return pl.DataFrame()


def get_margin_matrix(conn, period: str = "ALL"):
    """Margin matrix: qty_sold vs margin_pct for products with sales."""
    try:
        return conn.execute("""
            SELECT
                full_name,
                category,
                qty_sold,
                revenue,
                margin_pct,
                abc_class
            FROM products
            WHERE qty_sold > 0
            ORDER BY revenue DESC
        """).pl()
    except Exception:
        return pl.DataFrame()


def get_stock_turnover(conn):
    """Stock turnover (giro) per product."""
    try:
        return conn.execute("""
            SELECT
                i.product,
                i.category,
                i.current_stock,
                i.min_stock,
                COALESCE(p.qty_sold, 0)                                  AS qty_sold,
                ROUND(
                    COALESCE(p.qty_sold, 0)::FLOAT /
                    NULLIF(i.current_stock, 0)
                , 2)                                                     AS giro,
                CASE
                    WHEN i.current_stock = 0                             THEN '⚠️ Sem estoque'
                    WHEN COALESCE(p.qty_sold,0)::FLOAT /
                         NULLIF(i.current_stock,0) >= 3                  THEN '🔥 Alto'
                    WHEN COALESCE(p.qty_sold,0)::FLOAT /
                         NULLIF(i.current_stock,0) >= 1                  THEN '✅ Normal'
                    ELSE                                                       '🐢 Baixo'
                END                                                      AS giro_class
            FROM inventory i
            LEFT JOIN products p ON lower(i.product) = lower(p.full_name)
            ORDER BY giro DESC NULLS LAST
        """).pl()
    except Exception:
        return pl.DataFrame()


def get_inventory_alerts(conn):
    """Products at or below minimum stock."""
    try:
        return conn.execute("""
            SELECT
                product,
                category,
                current_stock,
                min_stock,
                CASE
                    WHEN current_stock <= min_stock * 0.5 THEN '🔴 Crítico'
                    WHEN current_stock <= min_stock       THEN '🟡 Baixo'
                    ELSE                                       '🟢 OK'
                END AS alert
            FROM inventory
            ORDER BY current_stock::FLOAT / NULLIF(min_stock::FLOAT, 0) ASC
        """).pl()
    except Exception:
        return pl.DataFrame()


def get_cashflow_summary(conn):
    """Cashflow totals by type."""
    try:
        return conn.execute("""
            SELECT
                Type,
                Category,
                SUM(Amount) AS total
            FROM cashflow
            GROUP BY Type, Category
            ORDER BY Type, total DESC
        """).pl()
    except Exception:
        return pl.DataFrame()


def get_daily_sales_trend(conn, top_n: int = 10):
    """Daily revenue trend for top N products."""
    try:
        return conn.execute(f"""
            SELECT Date, Product, SUM(Total) AS revenue
            FROM sales
            WHERE Product IN (
                SELECT Product FROM sales
                GROUP BY Product
                ORDER BY SUM(Total) DESC
                LIMIT {top_n}
            )
            GROUP BY Date, Product
            ORDER BY Date
        """).pl()
    except Exception:
        return pl.DataFrame()


# ── Kept for sidebar compatibility (no-op period filter) ──────────────────────
PERIOD_OPTIONS: dict[str, str] = {
    "2026 (Mar–Abr+)": "ALL",
}


def get_selected_period() -> str:
    return "ALL"
