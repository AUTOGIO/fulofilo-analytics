#!/usr/bin/env python3
"""
Import a POS item-sales summary CSV into the canonical FulôFiló workbook.

This script intentionally uses only the Python standard library. It updates the
canonical workbook first; generated parquet/DuckDB layers remain reproducible by
running scripts/sync_excel.sh after this import.
"""

from __future__ import annotations

import csv
import datetime as dt
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "data" / "excel" / "FuloFilo_Master.xlsx"
BACKUPS = ROOT / "data" / "excel" / "backups"
RAW = ROOT / "data" / "raw"
SHEET_DAILY_SALES = "xl/worksheets/sheet3.xml"
SHEET_CASHFLOW = "xl/worksheets/sheet4.xml"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
ET.register_namespace("", NS["m"])

# Loyverse sometimes exports month-to-date totals while the filename says a single day.
SINGLE_DAY_MAX_REVENUE = 10_000.0


def usage() -> None:
    print("Usage: python3 scripts/import_sales_summary_to_excel.py /path/item_sales_summary_YYYY-MM-DD_YYYY-MM-DD.csv")


def period_from_name(path: Path) -> tuple[dt.date, dt.date, str]:
    match = re.search(r"(\d{4}-\d{2}-\d{2})[-_](\d{4}-\d{2}-\d{2})", path.stem)
    if not match:
        raise SystemExit(f"Could not find YYYY-MM-DD date range in filename: {path.name}")
    start = dt.date.fromisoformat(match.group(1))
    end = dt.date.fromisoformat(match.group(2))
    if end < start:
        raise SystemExit(f"Invalid date range in filename: {path.name}")
    source = f"item_sales_summary_{start.isoformat()}_{end.isoformat()}"
    return start, end, source


def parse_float(value: object) -> float:
    text = str(value or "0").strip().replace("%", "").replace(",", ".")
    return float(text) if text else 0.0


def working_days(start: dt.date, end: dt.date) -> list[dt.date]:
    days: list[dt.date] = []
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 6:
            days.append(cursor)
        cursor += dt.timedelta(days=1)
    return days or [start]


def col_to_index(col: str) -> int:
    value = 0
    for char in col:
        value = value * 26 + (ord(char.upper()) - 64)
    return value


def cell_col(ref: str) -> int:
    return col_to_index(re.match(r"[A-Z]+", ref).group(0))


def cell_text(cell: ET.Element) -> str:
    if cell.attrib.get("t") == "inlineStr":
        node = cell.find("m:is/m:t", NS)
        return "" if node is None or node.text is None else node.text
    node = cell.find("m:v", NS)
    return "" if node is None or node.text is None else node.text


def read_sheet_rows(xml: bytes) -> list[list[str]]:
    root = ET.fromstring(xml)
    rows: list[list[str]] = []
    for row in root.findall(".//m:sheetData/m:row", NS):
        values: dict[int, str] = {}
        for cell in row.findall("m:c", NS):
            values[cell_col(cell.attrib["r"])] = cell_text(cell)
        width = max(values.keys(), default=0)
        rows.append([values.get(i, "") for i in range(1, width + 1)])
    return rows


def xesc(value: object) -> str:
    text = str(value if value is not None else "")
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def cell(ref: str, value: object, numeric: bool = False, style: str = "") -> str:
    style_attr = f' s="{style}"' if style else ""
    if numeric:
        return f'<c r="{ref}"{style_attr} t="n"><v>{value}</v></c>'
    return f'<c r="{ref}"{style_attr} t="inlineStr"><is><t>{xesc(value)}</t></is></c>'


def sheet_xml(headers: list[str], rows: list[list[object]], numeric_cols: set[int]) -> str:
    max_col = chr(ord("A") + len(headers) - 1)
    max_row = len(rows) + 1
    out = [
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        f'<dimension ref="A1:{max_col}{max_row}" />',
        '<sheetViews><sheetView workbookViewId="0"><selection activeCell="A1" sqref="A1" /></sheetView></sheetViews>',
        '<sheetFormatPr baseColWidth="8" defaultColWidth="12" defaultRowHeight="15" />',
        "<sheetData>",
        '<row r="1" ht="15" customHeight="1" s="1">',
    ]
    for idx, header in enumerate(headers, start=1):
        ref = f"{chr(ord('A') + idx - 1)}1"
        out.append(cell(ref, header, style="2"))
    out.append("</row>")
    for r_idx, row in enumerate(rows, start=2):
        out.append(f'<row r="{r_idx}">')
        for c_idx, value in enumerate(row, start=1):
            ref = f"{chr(ord('A') + c_idx - 1)}{r_idx}"
            out.append(cell(ref, value, numeric=c_idx in numeric_cols))
        out.append("</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)


def read_sales_summary(path: Path) -> tuple[list[dict[str, object]], float, float, float]:
    sales: list[dict[str, object]] = []
    units = revenue = cost = 0.0
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"Item", "SKU", "Itens vendidos", "Vendas líquidas", "Custo das mercadorias"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"CSV missing required columns: {sorted(missing)}")
        for raw in reader:
            item = str(raw.get("Item") or "").strip()
            sku = str(raw.get("SKU") or "").strip()
            qty = parse_float(raw.get("Itens vendidos"))
            rev = parse_float(raw.get("Vendas líquidas"))
            cmv = parse_float(raw.get("Custo das mercadorias"))
            if not item or not sku or qty <= 0 or rev <= 0:
                continue
            sales.append({"item": item, "sku": sku, "qty": qty, "revenue": rev, "cost": cmv})
            units += qty
            revenue += rev
            cost += cmv
    if not sales:
        raise SystemExit("CSV contains no valid sales rows.")
    return sales, units, revenue, cost


def in_period(value: str, start: dt.date, end: dt.date) -> bool:
    try:
        parsed = dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return False
    return start <= parsed <= end


def main() -> None:
    if len(sys.argv) != 2:
        usage()
        raise SystemExit(2)

    csv_path = Path(sys.argv[1]).expanduser().resolve()
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")
    if not MASTER.exists():
        raise SystemExit(f"Workbook not found: {MASTER}")

    start, end, source = period_from_name(csv_path)
    sales, units, revenue, cost = read_sales_summary(csv_path)
    days = working_days(start, end)
    span_days = (end - start).days + 1
    if span_days > 31 and len(days) > 1:
        print(
            f"WARNING: {csv_path.name} spans {span_days} calendar days — "
            "totals are spread evenly across working days (estimates, not POS daily truth). "
            "Prefer one CSV per day from Loyverse for real month/week charts."
        )
    if start == end:
        print(f"NOTE: single-day import — daily figures match POS for {start.isoformat()}.")
        if revenue > SINGLE_DAY_MAX_REVENUE:
            raise SystemExit(
                f"Single-day import rejected: R$ {revenue:,.2f} on {start.isoformat()} "
                "looks like a cumulative period export, not one POS day. "
                f"Re-export Loyverse item sales for exactly {start.isoformat()}."
            )

    BACKUPS.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUPS / f"FuloFilo_Master_before_{source}_{ts}.xlsx"
    shutil.copy2(MASTER, backup)

    with zipfile.ZipFile(MASTER, "r") as zin:
        daily_rows = read_sheet_rows(zin.read(SHEET_DAILY_SALES))
        cashflow_rows = read_sheet_rows(zin.read(SHEET_CASHFLOW))
        original_entries = {name: zin.read(name) for name in zin.namelist()}

    kept_daily = [
        row[:8]
        for row in daily_rows[1:]
        if row and len(row) >= 1 and not in_period(row[0], start, end)
    ]
    new_daily: list[list[object]] = []
    for record in sales:
        qty_per_day = float(record["qty"]) / len(days)
        unit_price = float(record["revenue"]) / float(record["qty"])
        total_per_day = float(record["revenue"]) / len(days)
        for day in days:
            new_daily.append([
                day.isoformat(),
                record["sku"],
                record["item"],
                qty_per_day,
                unit_price,
                total_per_day,
                "Misto",
                source,
            ])

    kept_cashflow = []
    for row in cashflow_rows[1:]:
        if not row:
            continue
        date_value = row[0] if len(row) > 0 else ""
        category = str(row[2] if len(row) > 2 else "")
        description = str(row[3] if len(row) > 3 else "")
        is_sales_period = in_period(date_value, start, end) and (
            category.lower() in {"vendas", "cmv"} or "vendas" in description.lower() or "cmv" in description.lower()
        )
        if not is_sales_period:
            kept_cashflow.append((row + [""] * 6)[:6])
    kept_cashflow.extend([
        [start.isoformat(), "Receita", "Vendas", f"Vendas {start.isoformat()} -> {end.isoformat()}", revenue, "Misto"],
        [start.isoformat(), "Despesa", "CMV", f"CMV {start.isoformat()} -> {end.isoformat()}", cost, "Misto"],
    ])

    daily_headers = ["Date", "sku", "Product", "Quantity", "Unit_Price", "Total", "Payment_Method", "Source"]
    cashflow_headers = ["Date", "Type", "Category", "Description", "Amount", "Payment_Method"]
    original_entries[SHEET_DAILY_SALES] = sheet_xml(daily_headers, kept_daily + new_daily, {4, 5, 6}).encode()
    original_entries[SHEET_CASHFLOW] = sheet_xml(cashflow_headers, kept_cashflow, {5}).encode()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp_path = Path(tmp.name)
    try:
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for name, content in original_entries.items():
                zout.writestr(name, content)
        shutil.move(tmp_path, MASTER)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    RAW.mkdir(parents=True, exist_ok=True)
    raw_copy = RAW / f"{source}.csv"
    if csv_path.resolve() != raw_copy.resolve():
        shutil.copy2(csv_path, raw_copy)

    print(f"Imported {len(sales)} products across {len(days)} operating days")
    print(f"Units: {units:.3f}")
    print(f"Revenue: {revenue:.2f}")
    print(f"COGS: {cost:.2f}")
    print(f"Backup: {backup}")
    print(f"Archived source: {raw_copy}")


if __name__ == "__main__":
    main()
