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
    
    if (DATA_DIR / "daily_sales.parquet").exists():
        conn.execute(f"CREATE OR REPLACE VIEW sales AS SELECT * FROM read_parquet('{DATA_DIR}/daily_sales.parquet');")
        
    if (DATA_DIR / "inventory.parquet").exists():
        conn.execute(f"CREATE OR REPLACE VIEW inventory AS SELECT * FROM read_parquet('{DATA_DIR}/inventory.parquet');")
        
    if (DATA_DIR / "cashflow.parquet").exists():
        conn.execute(f"CREATE OR REPLACE VIEW cashflow AS SELECT * FROM read_parquet('{DATA_DIR}/cashflow.parquet');")
        
    return conn

# --- Analytical Queries ---

def get_summary_kpis(conn):
    """Get high-level KPIs for the dashboard."""
    try:
        return conn.execute("""
            SELECT
                SUM(revenue) AS receita,
                SUM(qty_sold) AS quantidade,
                SUM(profit) AS lucro,
                ROUND(SUM(revenue) / NULLIF(SUM(qty_sold), 0), 2) AS ticket_medio
            FROM products
        """).fetchone()
    except duckdb.CatalogException:
        return (0, 0, 0, 0)

def get_abc_analysis(conn):
    """Return ABC classification data."""
    try:
        return conn.execute("""
            SELECT
                full_name,
                category,
                revenue,
                qty_sold,
                profit,
                abc_class
            FROM products
            ORDER BY revenue DESC
        """).pl()
    except duckdb.CatalogException:
        return pl.DataFrame()

def get_margin_matrix(conn):
    """Return data for the Margin Matrix scatter plot."""
    try:
        return conn.execute("""
            SELECT
                full_name,
                category,
                qty_sold,
                revenue,
                margin_pct
            FROM products
            WHERE qty_sold > 0
        """).pl()
    except duckdb.CatalogException:
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
