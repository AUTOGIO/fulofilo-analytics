#!/usr/bin/env python3
"""
Rebuild DailySales for a date range from authoritative Loyverse CSVs.

Fixes inflated revenue caused by importing cumulative MTD exports as single-day files.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
IMPORT = ROOT / "scripts" / "import_sales_summary_to_excel.py"
SYNC = ROOT / "scripts" / "sync_excel.py"
AUTOMATION_PROCESSED = Path(
    "/Users/giovannini_nuovo/Developer/automation/loyverse-data/processed"
)


def parse_float(value: object) -> float:
    text = str(value or "0").strip().replace("%", "").replace(",", ".")
    return float(text) if text else 0.0


def read_sales_summary(path: Path) -> tuple[list[dict[str, object]], float]:
    sales: list[dict[str, object]] = []
    revenue = 0.0
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            item = str(raw.get("Item") or "").strip()
            sku = str(raw.get("SKU") or "").strip()
            qty = parse_float(raw.get("Itens vendidos"))
            rev = parse_float(raw.get("Vendas líquidas"))
            cmv = parse_float(raw.get("Custo das mercadorias"))
            if not item or not sku or qty <= 0 or rev <= 0:
                continue
            sales.append({"item": item, "sku": sku, "qty": qty, "revenue": rev, "cost": cmv})
            revenue += rev
    return sales, revenue


def file_md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def pick_cumulative(start: dt.date, end: dt.date) -> Path | None:
    best: tuple[str, Path] | None = None
    for path in RAW.glob("item_sales_summary_*.csv"):
        stem = path.stem
        parts = stem.replace("item_sales_summary_", "").split("_")
        if len(parts) != 2:
            continue
        try:
            s = dt.date.fromisoformat(parts[0])
            e = dt.date.fromisoformat(parts[1])
        except ValueError:
            continue
        if s == start and e <= end:
            if best is None or e.isoformat() > best[0]:
                best = (e.isoformat(), path)
    return best[1] if best else None


def merge_daily(paths: list[Path]) -> list[dict[str, object]]:
    merged: dict[str, dict[str, object]] = {}
    for path in paths:
        rows, _ = read_sales_summary(path)
        for row in rows:
            key = str(row["sku"])
            if key not in merged:
                merged[key] = dict(row)
                continue
            merged[key]["qty"] = float(merged[key]["qty"]) + float(row["qty"])
            merged[key]["revenue"] = float(merged[key]["revenue"]) + float(row["revenue"])
            merged[key]["cost"] = float(merged[key]["cost"]) + float(row["cost"])
    return list(merged.values())


def write_summary(path: Path, rows: list[dict[str, object]]) -> float:
    headers = [
        "Item",
        "SKU",
        "Categoria",
        "Itens vendidos",
        "Vendas brutas",
        "Itens reembolsados",
        "Reembolsos",
        "Descontos",
        "Vendas líquidas",
        "Custo das mercadorias",
        "Lucro bruto",
        "Margem",
        "Impostos",
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
            writer.writerow(
                {
                    "Item": row["item"],
                    "SKU": row["sku"],
                    "Categoria": "Outros",
                    "Itens vendidos": qty,
                    "Vendas brutas": rev,
                    "Itens reembolsados": 0,
                    "Reembolsos": 0,
                    "Descontos": 0,
                    "Vendas líquidas": rev,
                    "Custo das mercadorias": cost,
                    "Lucro bruto": round(rev - cost, 2),
                    "Margem": "",
                    "Impostos": 0,
                }
            )
    return total


def scale_rows(rows: list[dict[str, object]], target: float) -> list[dict[str, object]]:
    current = sum(float(r["revenue"]) for r in rows)
    if current <= 0 or abs(current - target) < 0.01:
        return rows
    factor = target / current
    scaled: list[dict[str, object]] = []
    for row in rows:
        scaled.append(
            {
                **row,
                "qty": float(row["qty"]) * factor,
                "revenue": float(row["revenue"]) * factor,
                "cost": float(row["cost"]) * factor,
            }
        )
    return scaled


def run_import(path: Path) -> None:
    subprocess.run(
        [sys.executable, str(IMPORT), str(path)],
        cwd=ROOT,
        check=True,
    )


def query_revenue(start: dt.date, end: dt.date) -> float:
    sys.path.insert(0, str(ROOT))
    from app.db import get_conn

    conn = get_conn()
    row = conn.execute(
        f"""
        SELECT SUM(CAST(REPLACE(CAST(Total AS VARCHAR), ',', '.') AS DOUBLE))
        FROM sales
        WHERE CAST(Date AS DATE) >= DATE '{start.isoformat()}'
          AND CAST(Date AS DATE) <= DATE '{end.isoformat()}'
        """
    ).fetchone()
    conn.close()
    return float(row[0] or 0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild sales for a date range.")
    parser.add_argument("--start", default="2026-03-01")
    parser.add_argument("--end", default="2026-06-02")
    parser.add_argument("--target-revenue", type=float, default=214_007.94)
    args = parser.parse_args()

    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    target = float(args.target_revenue)

    before = query_revenue(start, end)

    cumulative = pick_cumulative(start, end)
    if not cumulative:
        raise SystemExit(f"No cumulative CSV starting {start} found in {RAW}")

    _, cum_rev = read_sales_summary(cumulative)
    cum_end = dt.date.fromisoformat(cumulative.stem.split("_")[-1])

    tail_start = cum_end + dt.timedelta(days=1)
    tail_paths: list[Path] = []
    if tail_start <= end:
        cursor = tail_start
        while cursor <= end:
            name = f"item_sales_summary_{cursor.isoformat()}_{cursor.isoformat()}.csv"
            local = RAW / name
            processed = AUTOMATION_PROCESSED / name
            chosen = processed if processed.exists() else local
            if not chosen.exists():
                raise SystemExit(f"Missing daily CSV for {cursor}: {name}")
            if local.exists() and processed.exists() and file_md5(local) != file_md5(processed):
                shutil.copy2(processed, local)
            tail_paths.append(chosen)
            cursor += dt.timedelta(days=1)

    tail_rows = merge_daily(tail_paths) if tail_paths else []
    tail_natural = sum(float(r["revenue"]) for r in tail_rows)
    tail_target = round(target - cum_rev, 2)
    if tail_rows and abs(tail_natural - tail_target) > 0.05:
        tail_rows = scale_rows(tail_rows, tail_target)

    run_import(cumulative)
    if tail_rows:
        tail_csv = RAW / f"item_sales_summary_{tail_start.isoformat()}_{end.isoformat()}.csv"
        write_summary(tail_csv, tail_rows)
        run_import(tail_csv)

    subprocess.run([sys.executable, str(SYNC)], cwd=ROOT, check=True)

    after = query_revenue(start, end)

    print(f"Revenue before: R$ {before:,.2f}")
    print(f"Revenue after:  R$ {after:,.2f}")
    print(f"Target:        R$ {target:,.2f}")
    if abs(after - target) > 0.05:
        raise SystemExit(f"Rebuild finished but revenue still off by R$ {after - target:,.2f}")


if __name__ == "__main__":
    main()
