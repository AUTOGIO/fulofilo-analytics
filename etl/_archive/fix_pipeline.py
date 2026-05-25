"""
FulôFiló — Pipeline Fix Script
===============================
Repairs three broken parquet files so build_report.py generates correct data:

  1. inventory.parquet   — rebuilt from products.parquet (adds 'sku' key)
  2. daily_sales.parquet — populated from vendas_marco_26.csv + vendas_abril_26.csv
  3. cashflow.parquet    — derived from the same CSVs (monthly Receita / Despesa)

Run:
    python etl/fix_pipeline.py
    python etl/fix_pipeline.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import datetime
from pathlib import Path

import polars as pl

BASE    = Path(__file__).resolve().parent.parent
RAW     = BASE / "data" / "raw"
OUT     = BASE / "data" / "parquet"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _write(df: pl.DataFrame, name: str, dry_run: bool) -> None:
    path = OUT / f"{name}.parquet"
    if dry_run:
        print(f"  [DRY-RUN] Would write {df.shape[0]} rows → {path.name}")
    else:
        df.write_parquet(path)
        print(f"  ✅ {name}.parquet — {df.shape[0]} rows")


def _parse_csv(path: Path) -> list[dict]:
    """Parse Eleve Vendas export CSV → list of dicts."""
    rows = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                rows.append({
                    "item":     row["Item"].strip(),
                    "sku":      row["SKU"].strip(),
                    "category": row["Categoria"].strip(),
                    "qty":      float(row["Itens vendidos"].replace(",", ".")),
                    "revenue":  float(row["Vendas líquidas"].replace(",", ".")),
                    "cost":     float(row["Custo das mercadorias"].replace(",", ".")),
                    "profit":   float(row["Lucro bruto"].replace(",", ".")),
                })
            except (KeyError, ValueError):
                continue
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# FIX 1 — inventory.parquet
# ══════════════════════════════════════════════════════════════════════════════

def fix_inventory(dry_run: bool) -> None:
    """
    Rebuild inventory.parquet from products.parquet.
    Uses existing current_stock where a product name matches, otherwise
    seeds with a default of 100 units.
    """
    print("\n── Fix 1: inventory.parquet ──────────────────────────────")

    products_path = OUT / "products.parquet"
    if not products_path.exists():
        print("  ⚠  products.parquet not found — skipping inventory fix")
        return

    products = pl.read_parquet(products_path)

    # Load old inventory to salvage any stock counts we can
    old_inv_path = OUT / "inventory.parquet"
    old_stock: dict[str, int] = {}
    if old_inv_path.exists():
        old = pl.read_parquet(old_inv_path)
        if "product" in old.columns and "current_stock" in old.columns:
            for row in old.iter_rows(named=True):
                old_stock[row["product"].strip()] = int(row["current_stock"] or 0)

    rows = []
    for row in products.iter_rows(named=True):
        name  = row["full_name"]
        stock = old_stock.get(name, 100)   # default 100 if no prior record
        rows.append({
            "sku":           row["sku"],
            "product":       name,
            "category":      row["category"],
            "current_stock": stock,
            "min_stock":     int(row.get("min_stock") or 10),
            "reorder_qty":   int(row.get("reorder_qty") or 30),
        })

    inv_df = pl.DataFrame(rows, schema={
        "sku":           pl.String,
        "product":       pl.String,
        "category":      pl.String,
        "current_stock": pl.Int64,
        "min_stock":     pl.Int64,
        "reorder_qty":   pl.Int64,
    })

    print(f"  Built {len(rows)} inventory rows from products.parquet")
    salvaged = sum(1 for r in rows if r["current_stock"] != 100)
    print(f"  Stock counts salvaged from old inventory: {salvaged}")
    _write(inv_df, "inventory", dry_run)


# ══════════════════════════════════════════════════════════════════════════════
# FIX 2 — daily_sales.parquet
# ══════════════════════════════════════════════════════════════════════════════

def fix_daily_sales(dry_run: bool) -> None:
    """
    Populate daily_sales.parquet from vendas_marco_26.csv + vendas_abril_26.csv.
    Since CSVs carry monthly totals, sales are distributed evenly across
    working days in each month (Mon–Sat). Payment method defaults to 'Misto'.
    """
    print("\n── Fix 2: daily_sales.parquet ────────────────────────────")

    csv_months: list[tuple[Path, int, int]] = [
        (RAW / "vendas_marco_26.csv",  2026, 3),
        (RAW / "vendas_abril_26.csv",  2026, 4),
    ]

    missing = [str(p) for p, _, _ in csv_months if not p.exists()]
    if missing:
        print(f"  ⚠  Missing CSVs: {missing}")
        return

    # Working days per month (Mon–Sat)
    def work_days(year: int, month: int) -> list[datetime.date]:
        import calendar
        days = []
        for d in range(1, calendar.monthrange(year, month)[1] + 1):
            dt = datetime.date(year, month, d)
            if dt.weekday() < 6:   # 0=Mon … 5=Sat
                days.append(dt)
        return days

    entries: list[dict] = []

    for csv_path, year, month in csv_months:
        rows   = _parse_csv(csv_path)
        w_days = work_days(year, month)
        n_days = len(w_days)

        for row in rows:
            if row["qty"] <= 0 or row["revenue"] <= 0:
                continue
            daily_qty     = row["qty"]     / n_days
            daily_revenue = row["revenue"] / n_days
            unit_price    = row["revenue"] / row["qty"] if row["qty"] else 0.0

            for day in w_days:
                entries.append({
                    "Date":           day.isoformat(),
                    "Product":        row["item"],
                    "Quantity":       round(daily_qty, 3),
                    "Unit_Price":     round(unit_price, 2),
                    "Total":          round(daily_revenue, 2),
                    "Payment_Method": "Misto",
                    "Source":         csv_path.stem,
                })

    if not entries:
        print("  ⚠  No valid rows found in CSVs")
        return

    ds_df = pl.DataFrame(entries, schema={
        "Date":           pl.String,
        "Product":        pl.String,
        "Quantity":       pl.Float64,
        "Unit_Price":     pl.Float64,
        "Total":          pl.Float64,
        "Payment_Method": pl.String,
        "Source":         pl.String,
    }).sort("Date")

    print(f"  Built {len(entries)} daily_sales entries across "
          f"{ds_df['Date'].n_unique()} dates from 2 CSVs")
    _write(ds_df, "daily_sales", dry_run)


# ══════════════════════════════════════════════════════════════════════════════
# FIX 3 — cashflow.parquet
# ══════════════════════════════════════════════════════════════════════════════

def fix_cashflow(dry_run: bool) -> None:
    """
    Derive cashflow.parquet from CSV monthly totals.
    Creates two entries per month: one Receita (revenue) and one Despesa (COGS).
    """
    print("\n── Fix 3: cashflow.parquet ───────────────────────────────")

    csv_months: list[tuple[Path, int, int]] = [
        (RAW / "vendas_marco_26.csv",  2026, 3),
        (RAW / "vendas_abril_26.csv",  2026, 4),
    ]

    missing = [str(p) for p, _, _ in csv_months if not p.exists()]
    if missing:
        print(f"  ⚠  Missing CSVs: {missing}")
        return

    entries: list[dict] = []

    for csv_path, year, month in csv_months:
        rows         = _parse_csv(csv_path)
        total_rev    = sum(r["revenue"] for r in rows)
        total_cost   = sum(r["cost"]    for r in rows)
        period_label = f"{year}-{month:02d}-01"

        if total_rev > 0:
            entries.append({
                "Date":           period_label,
                "Type":           "Receita",
                "Category":       "Vendas",
                "Description":    f"Vendas {csv_path.stem.replace('_', ' ').title()}",
                "Amount":         round(total_rev, 2),
                "Payment_Method": "Misto",
            })
        if total_cost > 0:
            entries.append({
                "Date":           period_label,
                "Type":           "Despesa",
                "Category":       "CMV",
                "Description":    f"Custo das Mercadorias {csv_path.stem.replace('_', ' ').title()}",
                "Amount":         round(total_cost, 2),
                "Payment_Method": "Misto",
            })

    if not entries:
        print("  ⚠  No cashflow entries derived")
        return

    cf_df = pl.DataFrame(entries, schema={
        "Date":           pl.String,
        "Type":           pl.String,
        "Category":       pl.String,
        "Description":    pl.String,
        "Amount":         pl.Float64,
        "Payment_Method": pl.String,
    }).sort("Date")

    for row in cf_df.iter_rows(named=True):
        print(f"  {row['Date']}  {row['Type']:<10}  R$ {row['Amount']:>10,.2f}  {row['Description']}")

    _write(cf_df, "cashflow", dry_run)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main(dry_run: bool = False) -> None:
    print("=" * 60)
    print("FulôFiló — Pipeline Fix")
    print(f"  mode: {'DRY-RUN (no writes)' if dry_run else 'EXECUTE'}")
    print("=" * 60)

    fix_inventory(dry_run)
    fix_daily_sales(dry_run)
    fix_cashflow(dry_run)

    print("\n" + "=" * 60)
    print("✅ Pipeline fix complete — run excel/build_report.py next")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FulôFiló pipeline fix")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
