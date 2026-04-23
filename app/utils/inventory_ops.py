"""
inventory_ops.py — Bidirectional Inventory Sync
================================================
Single source of truth for all inventory mutations:
  • decrement_stock()  — called by daily_ops when a sale is registered
  • adjust_stock()     — called by inventory page for manual corrections
  • sync_to_excel()    — writes current inventory.parquet → FuloFilo_Master.xlsx

Canonical write target: data/excel/FuloFilo_Master.xlsx  (Inventory sheet)
Generated report workbooks under excel/ are READ-ONLY outputs — never mutated here.

Excel column order (from sync_excel.py):
  A=sku  B=product  C=category  D=current_stock  E=min_stock
  F=reorder_qty  G=status  H=days_stock  I=stock_val

Audit trail: every stock mutation is appended to data/logs/stock_audit.csv
"""

import csv
import datetime
from pathlib import Path

import polars as pl
import openpyxl
from openpyxl.cell.cell import MergedCell

ROOT        = Path(__file__).resolve().parent.parent.parent
INV_PATH    = ROOT / "data" / "parquet" / "inventory.parquet"
MASTER_PATH = ROOT / "data" / "excel" / "FuloFilo_Master.xlsx"
LOG_PATH    = ROOT / "data" / "logs" / "stock_audit.csv"

# Fixed column indices in the Inventory sheet (1-based)
_COL_SKU           = 1
_COL_PRODUCT       = 2
_COL_CATEGORY      = 3
_COL_CURRENT_STOCK = 4
_COL_MIN_STOCK     = 5
_COL_REORDER_QTY   = 6
_HEADER_ROW        = 1
_DATA_START_ROW    = 2

_AUDIT_HEADERS = ["timestamp", "slug", "action", "qty_before", "qty_after", "delta"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_set(cell, value) -> None:
    if not isinstance(cell, MergedCell):
        cell.value = value


def _append_audit_log(slug: str, action: str, qty_before: int, qty_after: int) -> None:
    """Append one row to the append-only stock audit log."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not LOG_PATH.exists() or LOG_PATH.stat().st_size == 0
    with LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_AUDIT_HEADERS)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "timestamp":  datetime.datetime.now().isoformat(timespec="seconds"),
            "slug":       slug,
            "action":     action,
            "qty_before": qty_before,
            "qty_after":  qty_after,
            "delta":      qty_after - qty_before,
        })


def load_inventory() -> pl.DataFrame:
    return pl.read_parquet(INV_PATH) if INV_PATH.exists() else pl.DataFrame()


def save_inventory(df: pl.DataFrame) -> None:
    INV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(INV_PATH)


# ── Core mutations ────────────────────────────────────────────────────────────

def decrement_stock(product_name: str, qty: int) -> dict:
    """
    Find the inventory row whose 'product' best matches product_name and
    subtract qty from current_stock (floor 0).

    Matching strategy:
      1. Exact match (case-insensitive)
      2. Partial containment (longest product name that fits inside sale name)

    Returns a dict with result info, or {} if no match found.
    """
    df = load_inventory()
    if df.is_empty():
        return {}

    name_lower = product_name.strip().lower()

    # 1. Exact match
    exact = df.filter(pl.col("product").str.to_lowercase() == name_lower)
    if not exact.is_empty():
        match = exact[0]
    else:
        # 2. Partial: find products whose name appears inside the sale name
        candidates = df.filter(
            pl.col("product").str.to_lowercase().apply(
                lambda p: p in name_lower or name_lower in p,
                return_dtype=pl.Boolean,
            )
        )
        if candidates.is_empty():
            return {}
        # Pick the candidate with the longest matching name (most specific)
        match = candidates.sort("product", descending=True)[0]

    slug      = match["slug"][0]
    old_stock = int(match["current_stock"][0])
    new_stock = max(0, old_stock - qty)

    updated = df.with_columns(
        pl.when(pl.col("slug") == slug)
        .then(pl.lit(new_stock))
        .otherwise(pl.col("current_stock"))
        .alias("current_stock")
    )
    save_inventory(updated)
    _append_audit_log(slug, "decrement", old_stock, new_stock)
    sync_to_excel(updated)

    return {
        "slug":      slug,
        "product":   match["product"][0],
        "old_stock": old_stock,
        "new_stock": new_stock,
        "delta":     -(old_stock - new_stock),
    }


def adjust_stock(slug: str, new_qty: int) -> bool:
    """Directly set current_stock for a given slug. Returns True on success."""
    df = load_inventory()
    if df.is_empty():
        return False

    row = df.filter(pl.col("slug") == slug)
    old_stock = int(row["current_stock"][0]) if not row.is_empty() else 0
    clamped   = max(0, new_qty)

    updated = df.with_columns(
        pl.when(pl.col("slug") == slug)
        .then(pl.lit(clamped))
        .otherwise(pl.col("current_stock"))
        .alias("current_stock")
    )
    save_inventory(updated)
    _append_audit_log(slug, "adjust", old_stock, clamped)
    sync_to_excel(updated)
    return True


# ── Excel sync ────────────────────────────────────────────────────────────────

def sync_to_excel(df: pl.DataFrame | None = None) -> str | None:
    """
    Write inventory DataFrame back to FuloFilo_Master.xlsx (Inventory sheet).
    Matches rows by SKU (column A). Only updates cols D–F (stock values).

    Target: MASTER_PATH only. Generated report workbooks are read-only outputs
    and are never mutated by this function.

    Returns path to saved master workbook, or None on error.
    """
    if not MASTER_PATH.exists():
        print(f"[inventory_ops] Master workbook not found: {MASTER_PATH}")
        return None

    if df is None:
        df = load_inventory()
    if df.is_empty():
        return None

    try:
        wb  = openpyxl.load_workbook(MASTER_PATH)
        if "Inventory" not in wb.sheetnames:
            print("[inventory_ops] 'Inventory' sheet missing from master workbook.")
            return None
        ws  = wb["Inventory"]
        inv = df.to_pandas()

        # Build SKU → row index map (skip header row)
        sku_row: dict[str, int] = {}
        for r in range(_DATA_START_ROW, ws.max_row + 1):
            cell = ws.cell(row=r, column=_COL_SKU)
            if isinstance(cell, MergedCell) or cell.value is None:
                continue
            try:
                sku_row[str(int(float(str(cell.value)))).zfill(5)] = r
            except (ValueError, TypeError):
                continue

        # Write stock values back — only current_stock, min_stock, reorder_qty
        for _, row in inv.iterrows():
            slug = str(row["slug"]).zfill(5)
            r    = sku_row.get(slug)
            if r is None:
                continue
            _safe_set(ws.cell(row=r, column=_COL_CURRENT_STOCK), int(row["current_stock"]))
            _safe_set(ws.cell(row=r, column=_COL_MIN_STOCK),     int(row["min_stock"]))
            _safe_set(ws.cell(row=r, column=_COL_REORDER_QTY),   int(row["reorder_qty"]))

        wb.save(MASTER_PATH)
        return str(MASTER_PATH)

    except Exception as exc:  # noqa: BLE001
        print(f"[inventory_ops] sync_to_excel failed: {exc}")
        return None
