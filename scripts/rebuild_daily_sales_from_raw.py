#!/usr/bin/env python3
"""
Rebuild DailySales from archived raw item_sales_summary CSVs (real period slices).

1. Purge synthetic POS rows from 2026-03-01 onward (old cumulative spreads).
2. Import month/week slices, then single-day Loyverse exports (later wins).

Then: bash scripts/sync_excel.sh
"""

from __future__ import annotations

import datetime as dt
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.import_sales_summary_to_excel import (  # noqa: E402
    BACKUPS,
    MASTER,
    RAW,
    SHEET_CASHFLOW,
    SHEET_DAILY_SALES,
    in_period,
    read_sheet_rows,
    sheet_xml,
)

IMPORT = ROOT / "scripts" / "import_sales_summary_to_excel.py"

SKIP_STEMS = {
    "item_sales_summary_2026-03-01_2026-05-30",
    "item_sales_summary_2026-03-01_2026-05-27",
    "item_sales_summary_2026-03-01_2026-05-19",
    "item_sales_summary_2026-03-01_2026-04-26",
}

PURGE_FROM = date(2026, 3, 1)
PURGE_TO = date(2026, 12, 31)


def period_from_stem(stem: str) -> tuple[date, date, int] | None:
    m = re.search(r"(\d{4}-\d{2}-\d{2})[-_](\d{4}-\d{2}-\d{2})", stem)
    if not m:
        return None
    start = date.fromisoformat(m.group(1))
    end = date.fromisoformat(m.group(2))
    return start, end, (end - start).days


def ordered_files() -> list[Path]:
    files: list[Path] = []
    for path in RAW.glob("item_sales_summary*.csv"):
        stem = path.stem
        if stem in SKIP_STEMS or stem.endswith("_012853"):
            continue
        if period_from_stem(stem) is None:
            continue
        files.append(path)
    return sorted(
        files,
        key=lambda p: (
            -(period_from_stem(p.stem) or (date.min, date.min, 0))[2],
            (period_from_stem(p.stem) or (date.min, date.min, 0))[0],
            p.name,
        ),
    )


def purge_sales_window(start: date, end: date) -> None:
    """Remove DailySales and sales-related cashflow rows in [start, end]."""
    if not MASTER.exists():
        raise SystemExit(f"Workbook not found: {MASTER}")

    BACKUPS.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUPS / f"FuloFilo_Master_before_purge_{ts}.xlsx"
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
    removed_daily = len(daily_rows) - 1 - len(kept_daily)

    kept_cashflow = []
    removed_cf = 0
    for row in cashflow_rows[1:]:
        if not row:
            continue
        date_value = row[0] if len(row) > 0 else ""
        category = str(row[2] if len(row) > 2 else "")
        description = str(row[3] if len(row) > 3 else "")
        is_sales_period = in_period(date_value, start, end) and (
            category.lower() in {"vendas", "cmv", "receita", "despesa"}
            or "vendas" in description.lower()
            or "cmv" in description.lower()
        )
        if is_sales_period:
            removed_cf += 1
            continue
        kept_cashflow.append((row + [""] * 6)[:6])

    daily_headers = ["Date", "sku", "Product", "Quantity", "Unit_Price", "Total", "Payment_Method", "Source"]
    cashflow_headers = ["Date", "Type", "Category", "Description", "Amount", "Payment_Method"]
    original_entries[SHEET_DAILY_SALES] = sheet_xml(daily_headers, kept_daily, {4, 5, 6}).encode()
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

    print(f"Purged {removed_daily} DailySales rows and {removed_cf} cashflow rows in {start}..{end}")
    print(f"Backup: {backup}")


def main() -> int:
    files = ordered_files()
    if not files:
        print("No raw CSV files found.", file=sys.stderr)
        return 1

    print(f"Purging POS-derived rows from {PURGE_FROM} .. {PURGE_TO} ...")
    purge_sales_window(PURGE_FROM, PURGE_TO)

    print("\nRe-importing (wide periods first, single-day last):")
    for path in files:
        per = period_from_stem(path.stem)
        span = per[2] if per else "?"
        print(f"  [{span:>3}] {path.name}")

    for path in files:
        print(f"\n→ {path.name}")
        result = subprocess.run(
            [sys.executable, str(IMPORT), str(path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        print(result.stdout or "", end="")
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            return result.returncode

    print("\nRun: bash scripts/sync_excel.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
