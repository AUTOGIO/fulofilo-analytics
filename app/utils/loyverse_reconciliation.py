"""Reconcile Excel DailySales with an authoritative Loyverse period export."""

from __future__ import annotations

import datetime as dt
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from app.utils.automation_paths import loyverse_data_root, repo_root


ROOT = repo_root()
MASTER = ROOT / "data" / "excel" / "FuloFilo_Master.xlsx"
BACKUPS = ROOT / "data" / "excel" / "backups"
RAW = ROOT / "data" / "raw"
INCOMING = ROOT / "data" / "incoming"
SYNC_SCRIPT = ROOT / "scripts" / "sync_excel.sh"
IMPORT_SCRIPT = ROOT / "scripts" / "import_sales_summary_to_excel.py"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python3"
STATUS_PATH = ROOT / "data" / "excel" / "source_sync_status.json"

SHEET_DAILY_SALES = "xl/worksheets/sheet3.xml"
SHEET_CASHFLOW = "xl/worksheets/sheet4.xml"
DAILY_HEADERS = ["Date", "sku", "Product", "Quantity", "Unit_Price", "Total", "Payment_Method", "Source"]
CASHFLOW_HEADERS = ["Date", "Type", "Category", "Description", "Amount", "Payment_Method"]

DRIFT_TOLERANCE = 0.05
ANCHOR_GLOB = "*item*sales*summary*.csv"


@dataclass(frozen=True)
class ReconcileResult:
    ok: bool
    skipped: bool
    message: str
    anchor_path: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    anchor_revenue: float = 0.0
    ledger_revenue: float = 0.0
    drift_revenue: float = 0.0
    daily_files_imported: int = 0
    adjustments_applied: int = 0
    backup_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _import_helpers():
    from scripts.import_sales_summary_to_excel import (
        in_period,
        period_from_name,
        read_sales_summary,
        read_sheet_rows,
        sheet_xml,
    )

    return period_from_name, read_sales_summary, in_period, read_sheet_rows, sheet_xml


def normalize_anchor_path(path: Path) -> Path:
    """Copy Loyverse export into data/raw with canonical item_sales_summary naming."""
    path = path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Anchor CSV not found: {path}")

    period_from_name, _, _, _, _ = _import_helpers()
    start, end, source = period_from_name(path)
    RAW.mkdir(parents=True, exist_ok=True)
    canonical = RAW / f"{source}.csv"
    if path.resolve() != canonical.resolve():
        shutil.copy2(path, canonical)
    INCOMING.mkdir(parents=True, exist_ok=True)
    incoming_copy = INCOMING / path.name
    if path.resolve() != incoming_copy.resolve():
        shutil.copy2(path, incoming_copy)
    return canonical


def _period_from_stem(stem: str) -> tuple[dt.date, dt.date] | None:
    match = re.search(r"(\d{4}-\d{2}-\d{2})[-_](\d{4}-\d{2}-\d{2})", stem)
    if not match:
        return None
    start = dt.date.fromisoformat(match.group(1))
    end = dt.date.fromisoformat(match.group(2))
    if end < start:
        return None
    return start, end


def find_latest_anchor(*, search_roots: list[Path] | None = None) -> Path | None:
    """Return the Loyverse period export with the latest end date."""
    roots = search_roots or [
        INCOMING,
        RAW,
        ROOT / "data",
        loyverse_data_root() / "processed",
    ]
    candidates: list[tuple[dt.date, int, Path]] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.glob(ANCHOR_GLOB):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            period = _period_from_stem(path.stem)
            if period is None:
                continue
            start, end = period
            span = (end - start).days
            candidates.append((end, span, resolved))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1], item[2].name), reverse=True)
    return candidates[0][2]


def _single_day_revenue(path: Path) -> float:
    _, read_sales_summary, _, _, _ = _import_helpers()
    _, _, revenue, _ = read_sales_summary(path)
    return float(revenue)


def _is_valid_single_day_export(path: Path, *, max_revenue: float = 10_000.0) -> bool:
    period = _period_from_stem(path.stem)
    if period is None or period[0] != period[1]:
        return False
    try:
        return _single_day_revenue(path) <= max_revenue
    except Exception:
        return False


def collect_single_day_files(start: dt.date, end: dt.date) -> list[Path]:
    """Collect one CSV per calendar day (start==end) inside the period."""
    roots = [RAW, loyverse_data_root() / "processed"]
    by_day: dict[str, Path] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in root.glob("item_sales_summary_*_*.csv"):
            period = _period_from_stem(path.stem)
            if period is None:
                continue
            day_start, day_end = period
            if day_start != day_end:
                continue
            if day_start < start or day_start > end:
                continue
            if not _is_valid_single_day_export(path):
                continue
            key = day_start.isoformat()
            current = by_day.get(key)
            if current is None or path.stat().st_mtime >= current.stat().st_mtime:
                by_day[key] = path
    return [by_day[key] for key in sorted(by_day)]


def _backup_master() -> Path:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUPS / f"FuloFilo_Master_before_loyverse_reconcile_{ts}.xlsx"
    shutil.copy2(MASTER, backup)
    return backup


def _purge_sales_window(start: dt.date, end: dt.date) -> None:
    _, _, in_period, read_sheet_rows, sheet_xml = _import_helpers()
    with zipfile.ZipFile(MASTER, "r") as zin:
        daily_rows = read_sheet_rows(zin.read(SHEET_DAILY_SALES))
        cashflow_rows = read_sheet_rows(zin.read(SHEET_CASHFLOW))
        original_entries = {name: zin.read(name) for name in zin.namelist()}

    kept_daily = [
        row[:8]
        for row in daily_rows[1:]
        if row and len(row) >= 1 and not in_period(row[0], start, end)
    ]
    kept_cashflow = []
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
            or "loyverse_reconcile" in description.lower()
        )
        if is_sales_period:
            continue
        kept_cashflow.append((row + [""] * 6)[:6])

    original_entries[SHEET_DAILY_SALES] = sheet_xml(DAILY_HEADERS, kept_daily, {4, 5, 6}).encode()
    original_entries[SHEET_CASHFLOW] = sheet_xml(CASHFLOW_HEADERS, kept_cashflow, {5}).encode()
    _write_workbook(original_entries)


def _write_workbook(original_entries: dict[str, bytes]) -> None:
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


def _aggregate_daily_sales(start: dt.date, end: dt.date) -> dict[str, dict[str, float | str]]:
    sales = pd.read_excel(MASTER, sheet_name="DailySales", engine="openpyxl")
    sales.columns = [str(c).strip() for c in sales.columns]
    sales["Date"] = pd.to_datetime(sales["Date"], errors="coerce").dt.date
    sales = sales[(sales["Date"] >= start) & (sales["Date"] <= end)]
    sales["sku"] = sales["sku"].astype(str).str.strip()
    sales["Quantity"] = pd.to_numeric(sales["Quantity"], errors="coerce").fillna(0.0)
    sales["Total"] = pd.to_numeric(sales["Total"], errors="coerce").fillna(0.0)
    grouped = (
        sales.groupby("sku", as_index=False)
        .agg(
            qty=("Quantity", "sum"),
            revenue=("Total", "sum"),
            product=("Product", "last"),
        )
    )
    return {
        str(row["sku"]): {
            "qty": float(row["qty"]),
            "revenue": float(row["revenue"]),
            "product": str(row["product"]),
        }
        for _, row in grouped.iterrows()
        if str(row["sku"]).strip()
    }


def _catalog_names() -> dict[str, str]:
    catalog = pd.read_excel(MASTER, sheet_name="Catalog", engine="openpyxl")
    catalog.columns = [str(c).strip() for c in catalog.columns]
    names: dict[str, str] = {}
    for _, row in catalog.iterrows():
        sku = str(row.get("sku", "")).strip()
        if not sku:
            continue
        try:
            sku = str(int(float(sku))).zfill(5)
        except ValueError:
            sku = sku.zfill(5) if sku.isdigit() else sku
        names[sku] = str(row.get("full_name", "")).strip()
    return names


def _append_adjustments_and_cashflow(
    start: dt.date,
    end: dt.date,
    source: str,
    adjustments: list[dict[str, object]],
    anchor_revenue: float,
    anchor_cost: float,
) -> None:
    _, _, in_period, read_sheet_rows, sheet_xml = _import_helpers()
    with zipfile.ZipFile(MASTER, "r") as zin:
        daily_rows = read_sheet_rows(zin.read(SHEET_DAILY_SALES))
        cashflow_rows = read_sheet_rows(zin.read(SHEET_CASHFLOW))
        original_entries = {name: zin.read(name) for name in zin.namelist()}

    kept_daily = [row[:8] for row in daily_rows[1:] if row]
    kept_daily = [
        row
        for row in kept_daily
        if not (
            in_period(row[0], start, end)
            and len(row) >= 8
            and str(row[7]).startswith("loyverse_reconcile_")
        )
    ]

    reconcile_source = f"loyverse_reconcile_{source}"
    for adj in adjustments:
        qty = float(adj["qty"])
        revenue = float(adj["revenue"])
        unit_price = round(revenue / qty, 4) if qty else float(adj.get("unit_price") or 0.0)
        kept_daily.append(
            [
                end.isoformat(),
                adj["sku"],
                adj["product"],
                qty,
                unit_price,
                revenue,
                "Misto",
                reconcile_source,
            ]
        )

    kept_cashflow = []
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
            or "loyverse_reconcile" in description.lower()
        )
        if is_sales_period:
            continue
        kept_cashflow.append((row + [""] * 6)[:6])

    kept_cashflow.extend(
        [
            [end.isoformat(), "Receita", "Vendas", f"Loyverse anchor {start} -> {end}", anchor_revenue, "Misto"],
            [end.isoformat(), "Despesa", "CMV", f"Loyverse anchor CMV {start} -> {end}", anchor_cost, "Misto"],
        ]
    )

    original_entries[SHEET_DAILY_SALES] = sheet_xml(DAILY_HEADERS, kept_daily, {4, 5, 6}).encode()
    original_entries[SHEET_CASHFLOW] = sheet_xml(CASHFLOW_HEADERS, kept_cashflow, {5}).encode()
    _write_workbook(original_entries)


def _run_import(path: Path) -> None:
    runner = VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable)
    proc = subprocess.run(
        [str(runner), str(IMPORT_SCRIPT), str(path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "import failed").strip())


def _run_sync() -> None:
    proc = subprocess.run(["bash", str(SYNC_SCRIPT)], cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "sync failed").strip())


def compute_adjustments(
    anchor_rows: list[dict[str, object]],
    ledger_by_sku: dict[str, dict[str, float | str]],
    catalog_names: dict[str, str],
) -> list[dict[str, object]]:
    adjustments: list[dict[str, object]] = []
    for record in anchor_rows:
        sku = str(record["sku"]).strip()
        try:
            sku_key = str(int(float(sku))).zfill(5)
        except ValueError:
            sku_key = sku
        anchor_qty = float(record["qty"])
        anchor_rev = float(record["revenue"])
        current = ledger_by_sku.get(sku_key, {"qty": 0.0, "revenue": 0.0, "product": record["item"]})
        delta_qty = round(anchor_qty - float(current["qty"]), 6)
        delta_rev = round(anchor_rev - float(current["revenue"]), 2)
        if abs(delta_rev) <= DRIFT_TOLERANCE and abs(delta_qty) <= 0.001:
            continue
        product = catalog_names.get(sku_key) or str(current.get("product") or record["item"])
        unit_price = round(delta_rev / delta_qty, 4) if delta_qty else float(record["revenue"]) / max(float(record["qty"]), 1.0)
        adjustments.append(
            {
                "sku": sku_key,
                "product": product,
                "qty": delta_qty,
                "revenue": delta_rev,
                "unit_price": unit_price,
            }
        )
    return adjustments


def check_anchor_drift(sales: pd.DataFrame) -> dict[str, Any]:
    """Compare Excel DailySales totals with the latest Loyverse anchor file."""
    anchor = find_latest_anchor()
    if anchor is None:
        return {"configured": False}

    period_from_name, read_sales_summary, _, _, _ = _import_helpers()
    start, end, source = period_from_name(anchor)
    anchor_rows, _, anchor_revenue, _ = read_sales_summary(anchor)

    frame = sales.copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce").dt.date
    frame = frame[(frame["Date"] >= start) & (frame["Date"] <= end)]
    frame["Total"] = pd.to_numeric(frame["Total"], errors="coerce").fillna(0.0)
    ledger_revenue = float(frame["Total"].sum())
    drift = round(ledger_revenue - anchor_revenue, 2)

    return {
        "configured": True,
        "anchor_path": str(anchor),
        "anchor_source": source,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "anchor_revenue": round(float(anchor_revenue), 2),
        "ledger_revenue": round(ledger_revenue, 2),
        "drift_revenue": drift,
        "in_sync": abs(drift) <= DRIFT_TOLERANCE,
        "anchor_skus": len(anchor_rows),
    }


def reconcile_loyverse_period(
    *,
    anchor_path: Path | str | None = None,
    sync_after: bool = True,
) -> ReconcileResult:
    """Rebuild DailySales for the anchor period from daily CSVs + SKU-level adjustments."""
    if not MASTER.exists():
        return ReconcileResult(ok=False, skipped=True, message=f"Workbook not found: {MASTER}")

    period_from_name, read_sales_summary, _, _, _ = _import_helpers()
    anchor = normalize_anchor_path(Path(anchor_path)) if anchor_path else find_latest_anchor()
    if anchor is None:
        return ReconcileResult(ok=True, skipped=True, message="No Loyverse period anchor CSV found.")

    start, end, source = period_from_name(anchor)
    anchor_rows, _, anchor_revenue, anchor_cost = read_sales_summary(anchor)
    backup = _backup_master()

    _purge_sales_window(start, end)
    daily_files = collect_single_day_files(start, end)
    for path in daily_files:
        _run_import(path)

    ledger_by_sku = _aggregate_daily_sales(start, end)
    catalog_names = _catalog_names()
    adjustments = compute_adjustments(anchor_rows, ledger_by_sku, catalog_names)
    if adjustments:
        _append_adjustments_and_cashflow(start, end, source, adjustments, anchor_revenue, anchor_cost)
    else:
        _append_adjustments_and_cashflow(start, end, source, [], anchor_revenue, anchor_cost)

    ledger_revenue = sum(float(row["revenue"]) for row in ledger_by_sku.values())
    ledger_revenue += sum(float(adj["revenue"]) for adj in adjustments)
    drift = round(ledger_revenue - anchor_revenue, 2)

    if sync_after:
        _run_sync()

    drift_info = check_anchor_drift(pd.read_excel(MASTER, sheet_name="DailySales", engine="openpyxl"))
    message = (
        f"Reconciled {start} -> {end} against {anchor.name}; "
        f"R$ {ledger_revenue:,.2f} ledger vs R$ {anchor_revenue:,.2f} anchor."
    )
    return ReconcileResult(
        ok=abs(drift) <= DRIFT_TOLERANCE and drift_info.get("in_sync", False),
        skipped=False,
        message=message,
        anchor_path=str(anchor),
        period_start=start.isoformat(),
        period_end=end.isoformat(),
        anchor_revenue=round(float(anchor_revenue), 2),
        ledger_revenue=round(float(ledger_revenue), 2),
        drift_revenue=drift,
        daily_files_imported=len(daily_files),
        adjustments_applied=len(adjustments),
        backup_path=str(backup),
    )
