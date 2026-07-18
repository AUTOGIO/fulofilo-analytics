"""Tests for benchmarking helpers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import get_conn, get_supplier_summary


def test_supplier_summary_schema():
    conn = get_conn()
    try:
        df = get_supplier_summary(conn)
    finally:
        conn.close()
    if df.is_empty():
        return
    assert "supplier_name" in df.columns
