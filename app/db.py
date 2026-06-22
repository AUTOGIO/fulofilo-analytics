"""
FulôFiló — DuckDB Engine
=========================
Last updated: 26/04/2026 — added get_monthly_breakdown, forced cache invalidation
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
from datetime import datetime as _dt
from pathlib import Path
from typing import Literal
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

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        bootstrap = duckdb.connect(str(DB_PATH))
        bootstrap.close()

    # The dashboard only reads Parquet-backed views. Keep app sessions
    # in-memory so Streamlit reruns/pages never contend on the on-disk file.
    conn = duckdb.connect()

    if is_cloud:
        conn.execute("SET threads = 2")
        conn.execute("SET memory_limit = '512MB'")
    else:
        conn.execute("SET threads = 8")
        conn.execute("SET memory_limit = '8GB'")
    conn.execute("SET enable_progress_bar = false")
    conn.execute("SET temp_directory = '/tmp/duckdb_fulofilo'")

    # ── Standard views ────────────────────────────────────────────────────────
    for name, fname in [
        ("products",  "products.parquet"),
        ("sales",     "daily_sales.parquet"),
        ("cashflow",  "cashflow.parquet"),
    ]:
        p = DATA_DIR / fname
        if p.exists():
            if name == "products":
                conn.execute(
                    f"CREATE OR REPLACE VIEW {name} AS "
                    f"SELECT *, suggested_price AS price FROM read_parquet('{p}');"
                )
            elif name == "sales":
                sales_cols = set(pl.read_parquet(p, n_rows=0).columns)
                if "sku" in sales_cols:
                    conn.execute(
                        f"CREATE OR REPLACE VIEW {name} AS "
                        f"SELECT * FROM read_parquet('{p}');"
                    )
                else:
                    conn.execute(
                        f"CREATE OR REPLACE VIEW {name} AS "
                        f"SELECT *, CAST('' AS VARCHAR) AS sku FROM read_parquet('{p}');"
                    )
            else:
                conn.execute(
                    f"CREATE OR REPLACE VIEW {name} AS "
                    f"SELECT * FROM read_parquet('{p}');"
                )

    # ── Inventory view — live stock = baseline − sales since last sync ────────
    # inventory.parquet is written by sync_excel.py / ingest_catalog.
    # Its mtime marks the "restock date": any sales after that date are deducted
    # from current_stock so the dashboard always shows the real remaining stock.
    inv_p   = DATA_DIR / "inventory.parquet"
    sales_p = DATA_DIR / "daily_sales.parquet"
    supplier_p = DATA_DIR / "supplier_catalog.parquet"
    if supplier_p.exists():
        conn.execute(
            f"CREATE OR REPLACE VIEW supplier_catalog AS "
            f"SELECT * FROM read_parquet('{supplier_p}');"
        )
    else:
        conn.execute("""
            CREATE OR REPLACE VIEW supplier_catalog AS
            SELECT
                CAST('' AS VARCHAR) AS sku,
                CAST('' AS VARCHAR) AS supplier_id,
                CAST('' AS VARCHAR) AS supplier_name,
                CAST(12 AS INTEGER) AS lead_time_days,
                CAST(0 AS INTEGER) AS moq,
                CAST(1 AS INTEGER) AS case_pack
            WHERE 1=0
        """)

    if inv_p.exists():
        sync_date = _dt.fromtimestamp(inv_p.stat().st_mtime).date().isoformat()
        inv_cols = set(pl.read_parquet(inv_p, n_rows=0).columns)
        supplier_expr = "COALESCE(i.supplier, '')" if "supplier" in inv_cols else "''"
        lead_expr = "COALESCE(i.lead_time_days, 12)" if "lead_time_days" in inv_cols else "12"
        notes_expr = "COALESCE(i.notes, '')" if "notes" in inv_cols else "''"
        sales_cols = set(pl.read_parquet(sales_p, n_rows=0).columns) if sales_p.exists() else set()
        has_sku = "sku" in sales_cols

        if sales_p.exists():
            if has_sku:
                sold_join = f"""
                    LEFT JOIN (
                        SELECT
                            sku AS join_sku,
                            Product AS join_product,
                            CAST(SUM(Quantity) AS BIGINT) AS sold_since_sync
                        FROM read_parquet('{sales_p}')
                        WHERE Date >= '{sync_date}'
                        GROUP BY 1, 2
                    ) s ON i.sku = s.join_sku OR lower(i.product) = lower(s.join_product)
                """
            else:
                sold_join = f"""
                    LEFT JOIN (
                        SELECT
                            Product AS join_product,
                            CAST(SUM(Quantity) AS BIGINT) AS sold_since_sync
                        FROM read_parquet('{sales_p}')
                        WHERE Date >= '{sync_date}'
                        GROUP BY Product
                    ) s ON lower(i.product) = lower(s.join_product)
                """
            conn.execute(f"""
                CREATE OR REPLACE VIEW inventory AS
                SELECT
                    i.slug,
                    i.sku,
                    i.product,
                    i.category,
                    GREATEST(0,
                        CAST(i.current_stock AS BIGINT)
                        - COALESCE(s.sold_since_sync, 0)
                    )                          AS current_stock,
                    i.min_stock,
                    i.reorder_qty,
                    {supplier_expr}            AS supplier,
                    {lead_expr}                AS lead_time_days,
                    {notes_expr}               AS notes
                FROM read_parquet('{inv_p}') i
                {sold_join}
            """)
        else:
            extra = f", {supplier_expr} AS supplier, {lead_expr} AS lead_time_days, {notes_expr} AS notes"
            conn.execute(
                f"CREATE OR REPLACE VIEW inventory AS "
                f"SELECT slug, sku, product, category, current_stock, min_stock, reorder_qty"
                f"{extra} FROM read_parquet('{inv_p}');"
            )

    return conn


# ── Queries ────────────────────────────────────────────────────────────────────

def _period_filter(period: str) -> str:
    """Canonical Excel sync does not emit period slices; keep filters as a no-op."""
    return "1=1"


def get_summary_kpis(conn, period: str = "ALL"):
    """High-level KPIs: receita, unidades, lucro, ticket médio."""
    pf = _period_filter(period)
    try:
        return conn.execute(f"""
            SELECT
                SUM(revenue)                                               AS receita,
                SUM(qty_sold)                                              AS quantidade,
                SUM(profit)                                                AS lucro,
                ROUND(SUM(revenue) / NULLIF(SUM(qty_sold), 0), 2)         AS ticket_medio
            FROM products
            WHERE {pf}
        """).fetchone()
    except Exception:
        return (0, 0, 0, 0)


def get_abc_analysis(conn, period: str = "ALL"):
    """ABC data ordered by revenue descending."""
    pf = _period_filter(period)
    try:
        return conn.execute(f"""
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
            WHERE {pf}
            ORDER BY revenue DESC
        """).pl()
    except Exception:
        return pl.DataFrame()


def get_margin_matrix(conn, period: str = "ALL"):
    """Margin matrix: qty_sold vs margin_pct for products with sales."""
    pf = _period_filter(period)
    try:
        return conn.execute(f"""
            SELECT
                full_name,
                category,
                qty_sold,
                revenue,
                margin_pct,
                abc_class
            FROM products
            WHERE {pf}
              AND qty_sold > 0
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


def get_available_months(conn) -> list[str]:
    """Return sorted list of YYYY-MM strings present in the sales table."""
    try:
        rows = conn.execute("""
            SELECT DISTINCT strftime(CAST(Date AS DATE), '%Y-%m') AS mes
            FROM sales
            ORDER BY mes
        """).fetchall()
        return [r[0] for r in rows if r[0]]
    except Exception:
        return []


def get_monthly_breakdown(conn, months: list[str] | None = None):
    """Revenue and units grouped by year-month.

    Args:
        months: optional list of 'YYYY-MM' strings to filter.
                Pass None or [] to return all months.
    """
    try:
        where = ""
        if months:
            quoted = ", ".join(f"'{m}'" for m in months)
            where = f"WHERE strftime(CAST(Date AS DATE), '%Y-%m') IN ({quoted})"
        return conn.execute(f"""
            SELECT
                strftime(CAST(Date AS DATE), '%Y-%m')                                    AS mes,
                SUM(CAST(REPLACE(CAST(Total    AS VARCHAR), ',', '.') AS DOUBLE))         AS receita,
                SUM(CAST(REPLACE(CAST(Quantity AS VARCHAR), ',', '.') AS DOUBLE))         AS unidades
            FROM sales
            {where}
            GROUP BY mes
            ORDER BY mes
        """).pl()
    except Exception:
        return pl.DataFrame()


_PERIOD_QTY = "CAST(REPLACE(CAST(s.Quantity AS VARCHAR), ',', '.') AS DOUBLE)"
_PERIOD_TOTAL = "CAST(REPLACE(CAST(s.Total AS VARCHAR), ',', '.') AS DOUBLE)"


def get_executive_period_breakdown(
    conn,
    grain: Literal["month", "week"],
    *,
    fixed_total: float | None = None,
    limit: int = 12,
) -> pl.DataFrame:
    """Executive KPI metrics grouped by month or ISO week (last *limit* periods).

    Snapshot KPIs (low_critical, low_warn, ops_score) are always null in rows.
    sell_through and avg_turnover use current inventory as denominator (labeled in UI).
    """
    if grain == "month":
        period_expr = "strftime(CAST(s.Date AS DATE), '%Y-%m')"
    else:
        period_expr = "strftime(CAST(s.Date AS DATE), '%G-W%V')"

    if fixed_total is None:
        try:
            from app.utils.fixed_costs import load_fixed_costs

            _, fixed_total = load_fixed_costs()
        except Exception:
            fixed_total = 0.0
    fixed_total = float(fixed_total or 0.0)

    empty_cols = [
        "period_key",
        "receita",
        "unidades",
        "lucro",
        "margin_pct",
        "ticket",
        "burn_ratio",
        "sell_through",
        "avg_turnover",
        "low_critical",
        "low_warn",
        "ops_score",
    ]

    try:
        stock_row = conn.execute(
            "SELECT COALESCE(SUM(CAST(current_stock AS DOUBLE)), 0) FROM inventory"
        ).fetchone()
        current_stock_total = float(stock_row[0] or 0) if stock_row else 0.0
    except Exception:
        current_stock_total = 0.0

    try:
        df = conn.execute(
            f"""
            WITH line_sales AS (
                SELECT
                    {period_expr} AS period_key,
                    lower(s.Product) AS product_key,
                    s.Product AS product,
                    {_PERIOD_QTY} AS qty,
                    {_PERIOD_TOTAL} AS line_revenue,
                    {_PERIOD_TOTAL} - COALESCE(p.unit_cost, 0) * {_PERIOD_QTY} AS line_profit
                FROM sales s
                LEFT JOIN products p ON lower(s.Product) = lower(p.full_name)
            ),
            period_totals AS (
                SELECT
                    period_key,
                    SUM(line_revenue) AS receita,
                    SUM(qty) AS unidades,
                    SUM(line_profit) AS lucro
                FROM line_sales
                GROUP BY period_key
            ),
            period_sku AS (
                SELECT period_key, product_key, SUM(qty) AS period_qty
                FROM line_sales
                WHERE qty > 0
                GROUP BY period_key, product_key
            ),
            sku_turnover AS (
                SELECT
                    ps.period_key,
                    ps.period_qty::FLOAT / NULLIF(i.current_stock::FLOAT, 0) AS giro
                FROM period_sku ps
                LEFT JOIN inventory i ON ps.product_key = lower(i.product)
            ),
            turnover_agg AS (
                SELECT period_key, AVG(giro) AS avg_turnover
                FROM sku_turnover
                WHERE giro IS NOT NULL
                GROUP BY period_key
            ),
            ranked AS (
                SELECT
                    pt.period_key,
                    pt.receita,
                    pt.unidades,
                    pt.lucro,
                    CASE WHEN pt.receita > 0 THEN pt.lucro / pt.receita * 100 ELSE 0 END AS margin_pct,
                    CASE WHEN pt.unidades > 0 THEN pt.receita / pt.unidades ELSE 0 END AS ticket,
                    CASE WHEN pt.receita > 0 THEN {fixed_total} / pt.receita * 100 ELSE 0 END AS burn_ratio,
                    CASE
                        WHEN pt.unidades > 0 AND (pt.unidades + {current_stock_total}) > 0
                            THEN pt.unidades / (pt.unidades + {current_stock_total}) * 100
                        ELSE 0
                    END AS sell_through,
                    COALESCE(ta.avg_turnover, 0) AS avg_turnover
                FROM period_totals pt
                LEFT JOIN turnover_agg ta ON pt.period_key = ta.period_key
            )
            SELECT *
            FROM ranked
            ORDER BY period_key DESC
            LIMIT {int(limit)}
            """
        ).pl()
    except Exception:
        return pl.DataFrame(schema={c: pl.Float64 if c != "period_key" else pl.Utf8 for c in empty_cols})

    if df.is_empty():
        return pl.DataFrame(schema={c: pl.Float64 if c != "period_key" else pl.Utf8 for c in empty_cols})

    df = df.sort("period_key")
    df = df.with_columns(
        pl.lit(None, dtype=pl.Int64).alias("low_critical"),
        pl.lit(None, dtype=pl.Int64).alias("low_warn"),
        pl.lit(None, dtype=pl.Int64).alias("ops_score"),
    )
    return df.select(empty_cols)


def get_executive_monthly_breakdown(conn, **kwargs) -> pl.DataFrame:
    return get_executive_period_breakdown(conn, "month", **kwargs)


def get_executive_weekly_breakdown(conn, **kwargs) -> pl.DataFrame:
    return get_executive_period_breakdown(conn, "week", **kwargs)


def get_kpis_by_months(conn, months: list[str] | None = None):
    """KPIs (receita, unidades, ticket) directly from sales table, optionally filtered.

    Used when the user selects specific months — provides live figures
    instead of the pre-aggregated products parquet totals.
    Returns (receita, unidades, ticket_medio) or (0, 0, 0) on error.
    """
    try:
        where = ""
        if months:
            quoted = ", ".join(f"'{m}'" for m in months)
            where = f"AND strftime(CAST(Date AS DATE), '%Y-%m') IN ({quoted})"
        row = conn.execute(f"""
            SELECT
                SUM(CAST(REPLACE(CAST(Total    AS VARCHAR), ',', '.') AS DOUBLE))  AS receita,
                SUM(CAST(REPLACE(CAST(Quantity AS VARCHAR), ',', '.') AS DOUBLE))  AS unidades
            FROM sales
            WHERE 1=1 {where}
        """).fetchone()
        receita  = float(row[0]) if row and row[0] else 0.0
        unidades = float(row[1]) if row and row[1] else 0.0
        ticket   = round(receita / unidades, 2) if unidades else 0.0
        return receita, unidades, ticket
    except Exception:
        return 0.0, 0.0, 0.0


# ── Kept for sidebar compatibility (no-op period filter) ──────────────────────
PERIOD_OPTIONS: dict[str, str] = {
    "2026 (Mar–Abr+)": "ALL",
}


def get_selected_period() -> str:
    return "ALL"


def get_sales_timeseries(
    conn,
    grain: Literal["day", "week", "month"] = "day",
    *,
    sku: str | None = None,
    category: str | None = None,
) -> pl.DataFrame:
    """Sales time series aggregated by day/week/month."""
    if grain == "day":
        period_expr = "CAST(s.Date AS DATE)"
    elif grain == "week":
        period_expr = "strftime(CAST(s.Date AS DATE), '%G-W%V')"
    else:
        period_expr = "strftime(CAST(s.Date AS DATE), '%Y-%m')"

    filters = ["1=1"]
    if sku:
        filters.append(f"s.sku = '{sku}'")
    if category:
        filters.append(f"p.category = '{category}'")
    where = " AND ".join(filters)

    try:
        return conn.execute(f"""
            SELECT
                {period_expr} AS period,
                COALESCE(NULLIF(s.sku, ''), p.sku, '') AS sku,
                COALESCE(p.category, '') AS category,
                SUM(CAST(s.Quantity AS DOUBLE)) AS units,
                SUM(CAST(s.Total AS DOUBLE)) AS revenue
            FROM sales s
            LEFT JOIN products p ON s.sku = p.sku OR lower(s.Product) = lower(p.full_name)
            WHERE {where}
            GROUP BY 1, 2, 3
            ORDER BY period
        """).pl()
    except Exception:
        return pl.DataFrame()


def get_supplier_summary(conn) -> pl.DataFrame:
    """Reorder lines grouped by supplier with alert counts."""
    try:
        return conn.execute("""
            SELECT
                COALESCE(sc.supplier_id, '') AS supplier_id,
                COALESCE(sc.supplier_name, i.supplier, 'Não atribuído') AS supplier_name,
                COUNT(DISTINCT p.sku) AS sku_count,
                SUM(COALESCE(i.current_stock, 0)) AS total_stock,
                SUM(p.revenue) AS total_revenue
            FROM products p
            LEFT JOIN inventory i ON p.sku = i.sku
            LEFT JOIN supplier_catalog sc ON p.sku = sc.sku
            GROUP BY 1, 2
            ORDER BY total_revenue DESC
        """).pl()
    except Exception:
        return pl.DataFrame()
