#!/usr/bin/env python3
"""
FulôFiló — Excel master → Parquet sync
=======================================
Reads data/excel/FuloFilo_Master.xlsx (sheets Catalog, Inventory, DailySales,
Cashflow, CategoryOverrides, Meta), validates business rules, writes
data/parquet/*.parquet and data/excel/source_sync_status.json.

Usage:
  uv run python scripts/sync_excel.py
  uv run python scripts/sync_excel.py --sku-policy strict
  uv run python scripts/sync_excel.py --excel /path/to/FuloFilo_Master.xlsx
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import polars as pl

ROOT = Path(__file__).resolve().parent.parent
EXCEL_DIR = ROOT / "data" / "excel"
DEFAULT_XLSX = EXCEL_DIR / "FuloFilo_Master.xlsx"
PARQUET_DIR = ROOT / "data" / "parquet"
STATUS_PATH = EXCEL_DIR / "source_sync_status.json"

SHEET_CATALOG = "Catalog"
SHEET_INVENTORY = "Inventory"
SHEET_SALES = "DailySales"
SHEET_CASHFLOW = "Cashflow"
SHEET_OVERRIDES = "CategoryOverrides"
SHEET_META = "Meta"

TOL_SALES = 0.02

REQUIRED = {
    SHEET_CATALOG: ["sku", "full_name", "category", "unit_cost", "suggested_price", "min_stock", "reorder_qty"],
    SHEET_INVENTORY: ["sku", "product", "category", "current_stock", "min_stock", "reorder_qty"],
    SHEET_SALES: ["Date", "sku", "Product", "Quantity", "Unit_Price", "Total"],
    SHEET_CASHFLOW: ["Date", "Type", "Category", "Description", "Amount", "Payment_Method"],
    SHEET_OVERRIDES: ["sku", "category", "subcategory", "confidence"],
    SHEET_META: ["key", "value"],
}


def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _norm_sku(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v).strip()
    if not s:
        return ""
    try:
        return str(int(float(s))).zfill(5)
    except ValueError:
        return s


def _validate_columns(sheet: str, df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED[sheet] if c not in df.columns]
    if missing:
        raise SystemExit(f"[sync_excel] Sheet '{sheet}' missing columns: {missing}. Found: {list(df.columns)}")


def _read_sheet(xlsx: Path, name: str) -> pd.DataFrame:
    try:
        raw = pd.read_excel(xlsx, sheet_name=name, header=0, engine="openpyxl")
    except ValueError as e:
        raise SystemExit(f"[sync_excel] Cannot read sheet '{name}' from {xlsx}: {e}") from e
    return _norm_cols(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Excel master workbook to Parquet.")
    parser.add_argument("--excel", type=Path, default=DEFAULT_XLSX, help="Path to FuloFilo_Master.xlsx")
    parser.add_argument(
        "--sku-policy",
        choices=("balanced", "strict"),
        default="balanced",
        help="balanced: warn on blank SKU in sales; strict: error if blank SKU row has quantity > 0",
    )
    args = parser.parse_args()
    xlsx: Path = args.excel

    if not xlsx.exists():
        raise SystemExit(
            f"[sync_excel] Workbook not found: {xlsx}\n"
            "  Create it with: uv run python scripts/bootstrap_excel_master.py"
        )

    warnings: list[str] = []
    errors: list[str] = []

    cat = _read_sheet(xlsx, SHEET_CATALOG)
    inv = _read_sheet(xlsx, SHEET_INVENTORY)
    sales = _read_sheet(xlsx, SHEET_SALES)
    cf = _read_sheet(xlsx, SHEET_CASHFLOW)
    ov = _read_sheet(xlsx, SHEET_OVERRIDES)
    _meta = _read_sheet(xlsx, SHEET_META)

    for sheet_name, df in [
        (SHEET_CATALOG, cat),
        (SHEET_INVENTORY, inv),
        (SHEET_SALES, sales),
        (SHEET_CASHFLOW, cf),
        (SHEET_OVERRIDES, ov),
        (SHEET_META, _meta),
    ]:
        _validate_columns(sheet_name, df)

    cat["sku_norm"] = cat["sku"].map(_norm_sku)
    cat = cat[cat["sku_norm"] != ""].copy()
    if cat.empty:
        raise SystemExit("[sync_excel] Catalog has no rows with valid sku.")

    dup = cat[cat.duplicated("sku_norm", keep=False)]["sku_norm"].unique().tolist()
    if dup:
        raise SystemExit(f"[sync_excel] Duplicate SKU in Catalog: {dup[:20]}")

    for col in ("unit_cost", "suggested_price"):
        if (cat[col] < 0).any():
            bad = cat.loc[cat[col] < 0, "sku_norm"].tolist()
            raise SystemExit(f"[sync_excel] Negative {col} for SKU(s): {bad[:15]}")

    catalog_skus = set(cat["sku_norm"].tolist())

    inv["sku_norm"] = inv["sku"].map(_norm_sku)
    inv = inv[inv["sku_norm"] != ""].copy()
    orphan_inv = sorted(set(inv["sku_norm"]) - catalog_skus)
    if orphan_inv:
        raise SystemExit(f"[sync_excel] Inventory SKU not in Catalog: {orphan_inv[:20]}")

    ov = ov.copy()
    ov["sku_norm"] = ov["sku"].map(_norm_sku)
    ov = ov[ov["sku_norm"] != ""]
    orphan_ov = sorted(set(ov["sku_norm"]) - catalog_skus)
    if orphan_ov:
        raise SystemExit(f"[sync_excel] CategoryOverrides SKU not in Catalog: {orphan_ov[:20]}")

    sales = sales.copy()
    sales["sku_norm"] = sales["sku"].map(_norm_sku)
    if "Payment_Method" not in sales.columns:
        sales["Payment_Method"] = ""
    if "Source" not in sales.columns:
        sales["Source"] = "excel"

    blank_sales = sales[(sales["sku_norm"] == "") & (pd.to_numeric(sales["Quantity"], errors="coerce").fillna(0) > 0)]
    kpi_blank = int(blank_sales.shape[0])
    if kpi_blank:
        msg = f"{kpi_blank} DailySales row(s) have blank SKU but Quantity > 0 (KPI impact)."
        if args.sku_policy == "strict":
            errors.append(msg)
        else:
            warnings.append(msg)

    unknown_sales = sales[(sales["sku_norm"] != "") & (~sales["sku_norm"].isin(catalog_skus))]
    if not unknown_sales.empty:
        bad = unknown_sales["sku_norm"].unique().tolist()[:20]
        errors.append(f"DailySales SKU not in Catalog: {bad}")

    sales_chk = sales[sales["sku_norm"] != ""].copy()
    for _, r in sales_chk.iterrows():
        q = float(r["Quantity"] or 0)
        p = float(r["Unit_Price"] or 0)
        t = float(r["Total"] or 0)
        if q == 0 and t == 0:
            continue
        if abs(t - q * p) > TOL_SALES:
            errors.append(
                f"Sales row Date={r.get('Date')} SKU={r.get('sku_norm')}: "
                f"Total {t} != Quantity*Unit_Price ({q*p:.2f}), tol={TOL_SALES}"
            )

    if errors:
        _write_status(False, warnings, errors)
        raise SystemExit("[sync_excel] Validation failed:\n  - " + "\n  - ".join(errors))

    # Apply category overrides
    cat = cat.copy()
    for _, r in ov.iterrows():
        sku = r["sku_norm"]
        cat.loc[cat["sku_norm"] == sku, "category"] = r["category"]

    # Aggregate sales by SKU
    sales_valid = sales[sales["sku_norm"] != ""].copy()
    sales_valid["Quantity"] = pd.to_numeric(sales_valid["Quantity"], errors="coerce").fillna(0.0)
    sales_valid["Total"] = pd.to_numeric(sales_valid["Total"], errors="coerce").fillna(0.0)
    agg = (
        sales_valid.groupby("sku_norm", as_index=False)
        .agg(qty_sold=("Quantity", "sum"), revenue=("Total", "sum"))
    )

    cat_key = cat[["sku_norm", "full_name", "category", "unit_cost", "suggested_price", "min_stock", "reorder_qty"]].copy()
    cat_key = cat_key.rename(columns={"sku_norm": "sku"})

    products_pd = cat_key.merge(agg, left_on="sku", right_on="sku_norm", how="left")
    if "sku_norm" in products_pd.columns:
        products_pd = products_pd.drop(columns=["sku_norm"])
    products_pd["qty_sold"] = products_pd["qty_sold"].fillna(0.0)
    products_pd["revenue"] = products_pd["revenue"].fillna(0.0)
    products_pd["unit_cost"] = pd.to_numeric(products_pd["unit_cost"], errors="coerce").fillna(0.0)
    products_pd["suggested_price"] = pd.to_numeric(products_pd["suggested_price"], errors="coerce").fillna(0.0)

    products_pd["avg_price"] = products_pd.apply(
        lambda r: round(r["revenue"] / r["qty_sold"], 2) if r["qty_sold"] else r["suggested_price"],
        axis=1,
    )
    products_pd["unit_profit"] = products_pd["suggested_price"] - products_pd["unit_cost"]
    products_pd["margin_pct"] = products_pd.apply(
        lambda r: round((r["unit_profit"] / r["suggested_price"] * 100), 1) if r["suggested_price"] else 0.0,
        axis=1,
    )
    products_pd["profit"] = (products_pd["revenue"] - products_pd["unit_cost"] * products_pd["qty_sold"]).round(2)

    pl_prod = pl.from_pandas(products_pd)
    pl_prod = pl_prod.with_columns(
        pl.col("sku").cast(pl.Utf8),
        pl.col("sku").cast(pl.Utf8).alias("slug"),
    )

    total_rev = pl_prod["revenue"].sum()
    if total_rev and total_rev > 0:
        pl_prod = pl_prod.sort("revenue", descending=True)
        pl_prod = pl_prod.with_columns(pl.col("revenue").cum_sum().alias("cum_revenue"))
        pl_prod = pl_prod.with_columns(
            (pl.col("cum_revenue") / total_rev * 100).round(1).alias("cum_pct"),
            pl.when(pl.col("cum_revenue") / total_rev <= 0.80)
            .then(pl.lit("A"))
            .when(pl.col("cum_revenue") / total_rev <= 0.95)
            .then(pl.lit("B"))
            .otherwise(pl.lit("C"))
            .alias("abc_class"),
        )
    else:
        pl_prod = pl_prod.with_columns(
            pl.lit(0.0).alias("cum_revenue"),
            pl.lit(0.0).alias("cum_pct"),
            pl.lit("C").alias("abc_class"),
        )

    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    pl_prod.write_parquet(PARQUET_DIR / "products.parquet")

    inv_out = inv.copy().drop_duplicates(subset=["sku_norm"], keep="first")
    inv_out["sku"] = inv_out["sku_norm"]
    inv_out["slug"] = inv_out["sku_norm"]
    for c in ("current_stock", "min_stock", "reorder_qty"):
        inv_out[c] = pd.to_numeric(inv_out[c], errors="coerce").fillna(0).astype(int)
    extra_cols = ["supplier", "lead_time_days", "notes"]
    for c in extra_cols:
        if c not in inv_out.columns:
            inv_out[c] = "" if c != "lead_time_days" else 7
    inv_pl = pl.from_pandas(
        inv_out[["slug", "sku", "product", "category", "current_stock", "min_stock", "reorder_qty"]]
    )
    inv_pl.write_parquet(PARQUET_DIR / "inventory.parquet")

    ds = sales.copy()
    ds["Date"] = pd.to_datetime(ds["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    ds["Date"] = ds["Date"].fillna("")
    ds_pl = pl.DataFrame(
        {
            "Date": ds["Date"].astype(str),
            "Product": ds["Product"].astype(str),
            "Quantity": pd.to_numeric(ds["Quantity"], errors="coerce").fillna(0.0),
            "Unit_Price": pd.to_numeric(ds["Unit_Price"], errors="coerce").fillna(0.0),
            "Total": pd.to_numeric(ds["Total"], errors="coerce").fillna(0.0),
            "Payment_Method": ds["Payment_Method"].astype(str).fillna(""),
            "Source": ds["Source"].astype(str).fillna("excel"),
        }
    )
    ds_pl.write_parquet(PARQUET_DIR / "daily_sales.parquet")

    cf2 = cf.copy()
    cf2["Date"] = pd.to_datetime(cf2["Date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    cf_pl = pl.DataFrame(
        {
            "Date": cf2["Date"].astype(str),
            "Type": cf2["Type"].astype(str),
            "Category": cf2["Category"].astype(str),
            "Description": cf2["Description"].astype(str),
            "Amount": pd.to_numeric(cf2["Amount"], errors="coerce").fillna(0.0).abs(),
            "Payment_Method": cf2["Payment_Method"].astype(str).fillna(""),
        }
    )
    cf_pl.write_parquet(PARQUET_DIR / "cashflow.parquet")

    rev_r = pl_prod.select(
        pl.col("full_name").alias("item"),
        pl.col("qty_sold").alias("quantity"),
        pl.col("revenue").alias("revenue"),
    )
    rev_r.write_parquet(PARQUET_DIR / "revenue_report.parquet")

    qty_r = pl_prod.select(
        (pl.col("unit_cost") * pl.col("qty_sold")).round(2).alias("cost"),
        pl.col("full_name").alias("item"),
        pl.col("profit").alias("profit"),
        pl.col("qty_sold").alias("quantity"),
        pl.col("revenue").alias("revenue"),
    )
    qty_r.write_parquet(PARQUET_DIR / "quantity_report.parquet")

    prof_r = pl_prod.select(
        pl.col("sku").alias("code"),
        pl.col("full_name").alias("item"),
        pl.col("qty_sold").alias("quantity"),
        pl.col("profit").alias("total"),
    )
    prof_r.write_parquet(PARQUET_DIR / "profit_report.parquet")

    export_cat = pl_prod.select(
        [
            pl.col("sku"),
            pl.col("full_name"),
            pl.col("category"),
            pl.col("unit_cost"),
            pl.col("suggested_price"),
            pl.col("min_stock"),
            pl.col("reorder_qty"),
            pl.col("qty_sold"),
            pl.col("revenue"),
            pl.col("profit"),
            pl.col("margin_pct"),
        ]
    )
    export_cat.write_csv(ROOT / "data" / "raw" / "product_catalog.csv")

    _write_status(True, warnings, errors)
    if warnings:
        print("[sync_excel] Warnings:\n  - " + "\n  - ".join(warnings))
    print(f"[sync_excel] OK — Parquet written to {PARQUET_DIR}")


def _write_status(ok: bool, warnings: list[str], errors: list[str]) -> None:
    EXCEL_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": ok,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "warnings": warnings,
        "errors": errors,
    }
    STATUS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
