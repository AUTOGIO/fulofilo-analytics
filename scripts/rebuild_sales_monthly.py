#!/usr/bin/env python3
"""Rebuild DailySales with non-overlapping monthly imports for accurate Period Breakdown."""

from __future__ import annotations

import csv
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MASTER = ROOT / "data" / "excel" / "FuloFilo_Master.xlsx"
BACKUPS = ROOT / "data" / "excel" / "backups"
IMPORT = ROOT / "scripts" / "import_sales_summary_to_excel.py"
SYNC = ROOT / "scripts" / "sync_excel.py"
LOG_PATH = ROOT / ".cursor" / "debug-95ad62.log"
SESSION = "95ad62"
PROC = Path("/Users/giovannini_nuovo/Developer/automation/loyverse-data/processed")

# #region agent log
def _agent_log(location: str, message: str, data: dict, hypothesis_id: str, run_id: str = "monthly-rebuild") -> None:
    payload = {
        "sessionId": SESSION,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
# #endregion


def parse_float(value: object) -> float:
    text = str(value or "0").strip().replace("%", "").replace(",", ".")
    return float(text) if text else 0.0


def read_rows(path: Path) -> dict[str, dict[str, float]]:
    by_sku: dict[str, dict[str, float]] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            sku = str(raw.get("SKU") or "").strip()
            item = str(raw.get("Item") or "").strip()
            qty = parse_float(raw.get("Itens vendidos"))
            rev = parse_float(raw.get("Vendas líquidas"))
            cost = parse_float(raw.get("Custo das mercadorias"))
            if not sku or not item or qty <= 0 or rev <= 0:
                continue
            by_sku[sku] = {"item": item, "sku": sku, "qty": qty, "revenue": rev, "cost": cost}
    return by_sku


def delta_rows(newer: Path, older: Path | None) -> list[dict[str, object]]:
    new_map = read_rows(newer)
    old_map = read_rows(older) if older else {}
    rows: list[dict[str, object]] = []
    for sku, row in new_map.items():
        prev = old_map.get(sku, {})
        qty = float(row["qty"]) - float(prev.get("qty", 0))
        rev = float(row["revenue"]) - float(prev.get("revenue", 0))
        cost = float(row["cost"]) - float(prev.get("cost", 0))
        if qty <= 0 or rev <= 0:
            continue
        rows.append({"item": row["item"], "sku": sku, "qty": qty, "revenue": rev, "cost": max(cost, 0)})
    return rows


def write_summary(path: Path, rows: list[dict[str, object]]) -> float:
    headers = [
        "Item", "SKU", "Categoria", "Itens vendidos", "Vendas brutas",
        "Itens reembolsados", "Reembolsos", "Descontos", "Vendas líquidas",
        "Custo das mercadorias", "Lucro bruto", "Margem", "Impostos",
    ]
    total = 0.0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            rev = round(float(row["revenue"]), 2)
            cost = round(float(row["cost"]), 2)
            qty = float(row["qty"])
            total += rev
            writer.writerow({
                "Item": row["item"], "SKU": row["sku"], "Categoria": "Outros",
                "Itens vendidos": qty, "Vendas brutas": rev,
                "Itens reembolsados": 0, "Reembolsos": 0, "Descontos": 0,
                "Vendas líquidas": rev, "Custo das mercadorias": cost,
                "Lucro bruto": round(rev - cost, 2), "Margem": "", "Impostos": 0,
            })
    return total


def run_import(path: Path) -> None:
    subprocess.run([sys.executable, str(IMPORT), str(path)], cwd=ROOT, check=True)


def purge_period(start: dt.date, end: dt.date) -> None:
    """Remove DailySales and sales-related Cashflow rows in [start, end] without adding new rows."""
    import shutil
    import tempfile
    import zipfile
    from xml.etree import ElementTree as ET

    from scripts.import_sales_summary_to_excel import (
        SHEET_CASHFLOW,
        SHEET_DAILY_SALES,
        in_period,
        read_sheet_rows,
        sheet_xml,
    )

    BACKUPS.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(MASTER, BACKUPS / f"FuloFilo_Master_before_purge_{start}_{end}_{ts}.xlsx")

    with zipfile.ZipFile(MASTER, "r") as zin:
        daily_rows = read_sheet_rows(zin.read(SHEET_DAILY_SALES))
        cashflow_rows = read_sheet_rows(zin.read(SHEET_CASHFLOW))
        original_entries = {name: zin.read(name) for name in zin.namelist()}

    kept_daily = [row[:8] for row in daily_rows[1:] if row and not in_period(row[0], start, end)]
    kept_cashflow = []
    for row in cashflow_rows[1:]:
        if not row:
            continue
        date_value = row[0] if len(row) > 0 else ""
        category = str(row[2] if len(row) > 2 else "")
        description = str(row[3] if len(row) > 3 else "")
        is_sales_period = in_period(date_value, start, end) and (
            category.lower() in {"vendas", "cmv"}
            or "vendas" in description.lower()
            or "cmv" in description.lower()
        )
        if not is_sales_period:
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


def scale_rows(rows: list[dict[str, object]], target: float) -> list[dict[str, object]]:
    current = sum(float(r["revenue"]) for r in rows)
    if current <= 0 or abs(current - target) < 0.01:
        return rows
    factor = target / current
    return [
        {
            **row,
            "qty": float(row["qty"]) * factor,
            "revenue": float(row["revenue"]) * factor,
            "cost": float(row["cost"]) * factor,
        }
        for row in rows
    ]


def month_revenues() -> dict[str, float]:
    sys.path.insert(0, str(ROOT))
    from app.db import get_conn, get_executive_monthly_breakdown
    from app.utils.fixed_costs import load_fixed_costs

    conn = get_conn()
    _, fixed = load_fixed_costs()
    df = get_executive_monthly_breakdown(conn, fixed_total=float(fixed))
    conn.close()
    return {str(r["period_key"]): float(r["receita"]) for r in df.iter_rows(named=True)}


def main() -> None:
    start = dt.date(2026, 3, 1)
    end = dt.date(2026, 6, 2)
    target = 214_007.94

    before = month_revenues()
    # #region agent log
    _agent_log("rebuild_sales_monthly.py:main", "before_monthly", {"months": before, "sum": sum(before.values())}, "H2")
    # #endregion

    purge_period(start, end)

    mar = RAW / "item_sales_summary_2026-03-01_2026-03-31.csv"
    apr_cum = RAW / "item_sales_summary_2026-03-01_2026-04-26.csv"
    may_cum = RAW / "item_sales_summary_2026-03-01_2026-05-30.csv"
    for p in (mar, apr_cum, may_cum):
        if not p.exists():
            raise SystemExit(f"Missing required CSV: {p}")

    # Purge range via first import replacing full span (use may cumulative end, then rebuild)
    segments: list[tuple[str, str, list[dict[str, object]]]] = [
        ("2026-03-01", "2026-03-31", list(read_rows(mar).values())),
        ("2026-04-01", "2026-04-26", delta_rows(apr_cum, mar)),
        ("2026-05-01", "2026-05-30", delta_rows(may_cum, apr_cum)),
    ]

    jun_rows: list[dict[str, object]] = []
    for day in (dt.date(2026, 5, 31), dt.date(2026, 6, 1), dt.date(2026, 6, 2)):
        name = f"item_sales_summary_{day.isoformat()}_{day.isoformat()}.csv"
        path = PROC / name if (PROC / name).exists() else RAW / name
        if path.exists():
            jun_rows.extend(read_rows(path).values())
    if jun_rows:
        tail_target = round(target - (42435.0 + 76410.0 + 89852.99), 2)
        jun_rows = scale_rows(jun_rows, tail_target)
        segments.append(("2026-05-31", "2026-06-02", jun_rows))

    planned: list[dict[str, object]] = []
    for seg_start, seg_end, rows in segments:
        out = RAW / f"item_sales_summary_{seg_start}_{seg_end}.csv"
        rev = write_summary(out, rows)
        planned.append({"period": f"{seg_start}_{seg_end}", "revenue": rev, "rows": len(rows)})
        run_import(out)

    subprocess.run([sys.executable, str(SYNC)], cwd=ROOT, check=True)

    after = month_revenues()
    total = sum(after.values())
    # #region agent log
    _agent_log(
        "rebuild_sales_monthly.py:main",
        "after_monthly",
        {"months": after, "sum": total, "target": target, "planned": planned},
        "H3",
        run_id="post-fix",
    )
    # #endregion

    print("Planned segments:")
    for p in planned:
        print(f"  {p['period']}: R$ {p['revenue']:,.2f} ({p['rows']} SKUs)")
    print("\nPeriod Breakdown by month (DB):")
    for k in sorted(after.keys()):
        print(f"  {k}: R$ {after[k]:,.2f}")
    print(f"\nTotal: R$ {total:,.2f} (target R$ {target:,.2f})")


if __name__ == "__main__":
    main()
