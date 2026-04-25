"""
FulôFiló — DuckDB Engine
=========================
Handles the connection to the local DuckDB database and provides
analytical queries optimized for the M3 processor.
"""

import duckdb
from pathlib import Path
import polars as pl

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data" / "parquet"
DB_PATH = BASE / "data" / "fulofilo.duckdb"


def get_data_mtime() -> str:
    """Return a string fingerprint of the parquet directory's latest mtime.

    Pass this as a parameter to any @st.cache_data function to make it
    auto-invalidate whenever a parquet file is added, updated, or removed.
    Example:
        @st.cache_data
        def load(data_version: str):
            ...
        df = load(get_data_mtime())
    """
    mtimes = [
        p.stat().st_mtime
        for p in DATA_DIR.glob("*.parquet")
        if p.exists()
    ]
    return str(round(max(mtimes), 3)) if mtimes else "0"


def get_conn():
    """Initialize DuckDB connection and register Parquet files as views."""
    import os
    is_cloud = bool(os.environ.get("STREAMLIT_SHARING_MODE") or os.environ.get("IS_STREAMLIT_CLOUD"))

    conn = duckdb.connect(str(DB_PATH))

    # ── Performance Configuration (auto-tuned: M3 local vs Streamlit Cloud) ──
    if is_cloud:
        conn.execute("SET threads = 2")
        conn.execute("SET memory_limit = '512MB'")
    else:
        conn.execute("SET threads = 8")               # all M3 performance cores
        conn.execute("SET memory_limit = '8GB'")      # safe limit < 16GB unified
    conn.execute("SET enable_progress_bar = false")
    conn.execute("SET temp_directory = '/tmp/duckdb_fulofilo'")
    
    # Register views if Parquet files exist
    if (DATA_DIR / "products.parquet").exists():
        conn.execute(f"CREATE OR REPLACE VIEW products AS SELECT * FROM read_parquet('{DATA_DIR}/products.parquet');")

    # Period-specific views
    for period_label in ("2024", "2026"):
        p = DATA_DIR / f"products_{period_label}.parquet"
        if p.exists():
            conn.execute(f"CREATE OR REPLACE VIEW products_{period_label} AS SELECT * FROM read_parquet('{p}');")

    if (DATA_DIR / "daily_sales.parquet").exists():
        conn.execute(f"CREATE OR REPLACE VIEW sales AS SELECT * FROM read_parquet('{DATA_DIR}/daily_sales.parquet');")

    if (DATA_DIR / "inventory.parquet").exists():
        conn.execute(f"CREATE OR REPLACE VIEW inventory AS SELECT * FROM read_parquet('{DATA_DIR}/inventory.parquet');")

    if (DATA_DIR / "cashflow.parquet").exists():
        conn.execute(f"CREATE OR REPLACE VIEW cashflow AS SELECT * FROM read_parquet('{DATA_DIR}/cashflow.parquet');")

    return conn


# ── Period helpers ─────────────────────────────────────────────────────────────

PERIOD_OPTIONS: dict[str, str] = {
    "Mar–Abr 2026": "2026",
}

def period_where(period: str) -> str:
    """Return a SQL WHERE clause fragment for the given period selection.

    Parameters
    ----------
    period : "2026" or "ALL" (treated as 2026 — only real data)

    Returns
    -------
    str — e.g. "WHERE period = '2026'" or ""
    """
    if period == "ALL" or not period:
        return ""
    return f"WHERE period = '{period}'"


def period_and(period: str) -> str:
    """Return an AND clause for use inside an existing WHERE block."""
    if period == "ALL" or not period:
        return ""
    return f"AND period = '{period}'"

# --- Analytical Queries ---

def get_summary_kpis(conn, period: str = "ALL"):
    """Get high-level KPIs for the dashboard."""
    try:
        where = period_where(period)
        return conn.execute(f"""
            SELECT
                SUM(revenue) AS receita,
                SUM(qty_sold) AS quantidade,
                SUM(profit) AS lucro,
                ROUND(SUM(revenue) / NULLIF(SUM(qty_sold), 0), 2) AS ticket_medio
            FROM products
            {where}
        """).fetchone()
    except duckdb.CatalogException:
        return (0, 0, 0, 0)

def get_abc_analysis(conn, period: str = "ALL"):
    """Return ABC classification data ordered by abc_score (weighted rank)."""
    try:
        where = period_where(period)
        return conn.execute(f"""
            SELECT
                full_name,
                category,
                revenue,
                qty_sold,
                profit,
                abc_class,
                abc_score,
                period
            FROM products
            {where}
            ORDER BY abc_score DESC
        """).pl()
    except duckdb.CatalogException:
        return pl.DataFrame()

def get_margin_matrix(conn, period: str = "ALL"):
    """Return data for the Margin Matrix scatter plot."""
    try:
        where = period_where(period)
        and_clause = "AND qty_sold > 0" if period == "ALL" else "AND qty_sold > 0"
        # Build the WHERE properly
        if period == "ALL":
            filter_clause = "WHERE qty_sold > 0"
        else:
            filter_clause = f"WHERE period = '{period}' AND qty_sold > 0"
        return conn.execute(f"""
            SELECT
                full_name,
                category,
                qty_sold,
                revenue,
                margin_pct,
                period
            FROM products
            {filter_clause}
        """).pl()
    except duckdb.CatalogException:
        return pl.DataFrame()

def get_stock_turnover(conn):
    """Return stock turnover (giro) per product: qty_sold / current_stock."""
    try:
        return conn.execute("""
            SELECT
                i.product,
                i.category,
                i.current_stock,
                i.min_stock,
                COALESCE(p.qty_sold, 0)                              AS qty_sold,
                ROUND(
                    COALESCE(p.qty_sold, 0)::FLOAT /
                    NULLIF(i.current_stock, 0)
                , 2)                                                 AS giro,
                CASE
                    WHEN i.current_stock = 0                         THEN '⚠️ Sem estoque'
                    WHEN COALESCE(p.qty_sold,0)::FLOAT /
                         NULLIF(i.current_stock,0) >= 3              THEN '🔥 Alto'
                    WHEN COALESCE(p.qty_sold,0)::FLOAT /
                         NULLIF(i.current_stock,0) >= 1              THEN '✅ Normal'
                    ELSE                                                  '🐢 Baixo'
                END                                                  AS giro_class
            FROM inventory i
            LEFT JOIN products p ON lower(i.slug) = lower(p.raw_key)
            ORDER BY giro DESC NULLS LAST
        """).pl()
    except (duckdb.CatalogException, duckdb.BinderException):
        return pl.DataFrame()


def get_inventory_alerts(conn):
    """Return products below minimum stock."""
    try:
        return conn.execute("""
            SELECT
                product,
                category,
                current_stock,
                min_stock,
                CASE
                    WHEN current_stock <= min_stock * 0.5 THEN '🔴 Crítico'
                    WHEN current_stock <= min_stock THEN '🟡 Baixo'
                    ELSE '🟢 OK'
                END AS alert
            FROM inventory
            ORDER BY current_stock::FLOAT / NULLIF(min_stock::FLOAT, 0) ASC
        """).pl()
    except duckdb.CatalogException:
        return pl.DataFrame()
