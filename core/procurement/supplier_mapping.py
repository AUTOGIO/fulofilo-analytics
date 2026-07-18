"""Resolve supplier metadata for SKUs from inventory and supplier_catalog."""

from __future__ import annotations

import pandas as pd


def get_supplier_map(conn) -> pd.DataFrame:
    try:
        return conn.execute("""
            SELECT
                p.sku,
                p.full_name AS product,
                p.category,
                COALESCE(sc.supplier_id, '') AS supplier_id,
                COALESCE(sc.supplier_name, i.supplier, 'Não atribuído') AS supplier_name,
                COALESCE(
                    NULLIF(CAST(i.lead_time_days AS INTEGER), 0),
                    NULLIF(CAST(sc.lead_time_days AS INTEGER), 0),
                    12
                ) AS lead_time_days,
                COALESCE(NULLIF(CAST(sc.moq AS INTEGER), 0), 0) AS moq,
                COALESCE(NULLIF(CAST(sc.case_pack AS INTEGER), 0), 1) AS case_pack
            FROM products p
            LEFT JOIN inventory i ON p.sku = i.sku
            LEFT JOIN supplier_catalog sc ON p.sku = sc.sku
        """).df()
    except Exception:
        return pd.DataFrame()
