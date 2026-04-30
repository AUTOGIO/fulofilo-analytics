#!/usr/bin/env python3
"""
FulôFiló — Sales Drop Watcher
==============================
Drop a file in data/incoming/ → full pipeline runs automatically.

Workflow:
  1. Scan data/incoming/ for item-sales-summary-*.csv files
  2. Validate filename pattern + internal column signature
  3. Duplicate guard — warn if period already ingested
  4. Run etl/ingest.py → updates parquets + rebuilds analytics
  5. Sync back to FuloFilo_Master.xlsx (DailySales + Cashflow sheets)
  6. Archive file → data/raw/
  7. git commit + push → Streamlit Cloud redeploys (~90s)
  8. macOS notification — native alert when done

Usage:
    python scripts/sales_watcher.py            # process incoming/
    python scripts/sales_watcher.py --dry-run  # simulate, no writes
"""

from __future__ import annotations

import argparse
import csv
import datetime
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parent.parent
INCOMING    = ROOT / "data" / "incoming"
ARCHIVE     = ROOT / "data" / "raw"
LOGS_DIR    = ROOT / "logs"
LOG_FILE    = LOGS_DIR / "saleswatch.log"
INGEST      = ROOT / "etl" / "ingest.py"
EXCEL_MASTER = ROOT / "data" / "excel" / "FuloFilo_Master.xlsx"
EXCEL_BACKUP = ROOT / "data" / "excel" / "backups"
PARQUET_DIR  = ROOT / "data" / "parquet"

# ── File pattern ──────────────────────────────────────────────────────────────
FILENAME_RE = re.compile(
    r"^item-sales-summary-(\d{4}-\d{2}-\d{2})-(\d{4}-\d{2}-\d{2})\.csv$",
    re.IGNORECASE,
)

# Required columns (case-insensitive) — mirrors etl/ingest.py SALES_REQUIRED
REQUIRED_COLS = {"sku", "itens vendidos", "vendas líquidas", "custo das mercadorias"}

# ── Logging ───────────────────────────────────────────────────────────────────
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("saleswatch")


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _has_required_cols(path: Path) -> bool:
    try:
        with open(path, encoding="utf-8-sig") as f:
            header = next(csv.reader(f), [])
        cols = {c.lower().strip() for c in header}
        missing = REQUIRED_COLS - cols
        if missing:
            log.warning("  Column check failed — missing: %s", missing)
            return False
        return True
    except Exception as exc:
        log.error("  Could not read %s: %s", path.name, exc)
        return False


def _already_ingested(source_id: str) -> bool:
    """Return True if this source_id already exists in daily_sales.parquet."""
    ds_path = PARQUET_DIR / "daily_sales.parquet"
    if not ds_path.exists():
        return False
    try:
        import polars as pl
        ds = pl.read_parquet(ds_path)
        if "Source" in ds.columns:
            return source_id in ds["Source"].unique().to_list()
    except Exception:
        pass
    return False


def _run(cmd: list[str], cwd: Path, dry_run: bool, label: str) -> bool:
    if dry_run:
        log.info("  [DRY-RUN] %s: %s", label, " ".join(str(c) for c in cmd))
        return True
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            log.info("  ✅ %s", label)
            for line in result.stdout.strip().splitlines():
                log.info("     %s", line)
            return True
        else:
            log.error("  ❌ %s failed (exit %d)", label, result.returncode)
            if result.stderr.strip():
                log.error("     %s", result.stderr.strip()[:500])
            return False
    except subprocess.TimeoutExpired:
        log.error("  ❌ %s timed out", label)
        return False
    except Exception as exc:
        log.error("  ❌ %s error: %s", label, exc)
        return False


def _archive(path: Path, date_start: str, date_end: str, dry_run: bool) -> Path | None:
    canonical = f"item_sales_summary_{date_start}_{date_end}.csv"
    dest = ARCHIVE / canonical
    if dest.exists():
        ts = datetime.datetime.now().strftime("%H%M%S")
        dest = ARCHIVE / f"item_sales_summary_{date_start}_{date_end}_{ts}.csv"
    if dry_run:
        log.info("  [DRY-RUN] archive → data/raw/%s", dest.name)
        return dest
    try:
        shutil.move(str(path), str(dest))
        log.info("  📁 Archived → data/raw/%s", dest.name)
        return dest
    except Exception as exc:
        log.error("  ❌ Archive failed: %s", exc)
        return None


# ══════════════════════════════════════════════════════════════════════════════
# EXCEL MASTER SYNC
# ══════════════════════════════════════════════════════════════════════════════

def _sync_excel_master(source_id: str, date_start: str, date_end: str, dry_run: bool) -> bool:
    """
    Append new rows from parquet → FuloFilo_Master.xlsx (DailySales + Cashflow).
    Deduplicates by Source so re-runs are safe.
    """
    if not EXCEL_MASTER.exists():
        log.warning("  ⚠️  Excel Master not found — skipping Excel sync")
        return False

    try:
        import openpyxl
        import polars as pl
    except ImportError as exc:
        log.error("  ❌ Excel sync missing dependency: %s", exc)
        return False

    # ── Read new rows from parquet ────────────────────────────────────────────
    ds_path = PARQUET_DIR / "daily_sales.parquet"
    cf_path = PARQUET_DIR / "cashflow.parquet"

    if not ds_path.exists():
        log.warning("  ⚠️  daily_sales.parquet not found — skipping Excel sync")
        return False

    ds = pl.read_parquet(ds_path)
    new_sales = ds.filter(pl.col("Source") == source_id) if "Source" in ds.columns else pl.DataFrame()

    if new_sales.is_empty():
        log.info("  ℹ️  No rows for source_id '%s' in parquet — skipping Excel sync", source_id)
        return True

    if dry_run:
        log.info("  [DRY-RUN] Excel sync: %d DailySales rows + Cashflow entries", new_sales.shape[0])
        return True

    # ── Backup Excel before writing ───────────────────────────────────────────
    EXCEL_BACKUP.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = EXCEL_BACKUP / f"FuloFilo_Master_before_{source_id}_{ts}.xlsx"
    shutil.copy2(str(EXCEL_MASTER), str(backup_path))
    log.info("  💾 Excel backup → backups/%s", backup_path.name)

    # ── Open workbook ─────────────────────────────────────────────────────────
    wb = openpyxl.load_workbook(str(EXCEL_MASTER))

    # ── DailySales sheet ──────────────────────────────────────────────────────
    ws_sales = wb["DailySales"]

    # Remove existing rows for this source_id (safe re-run)
    rows_to_keep = []
    header = None
    for i, row in enumerate(ws_sales.iter_rows(values_only=True)):
        if i == 0:
            header = row
            continue
        # Source is last column
        if row and str(row[-1]) != source_id:
            rows_to_keep.append(row)

    # Rebuild sheet: clear data rows, re-write header + kept rows + new rows
    ws_sales.delete_rows(2, ws_sales.max_row)
    for row in rows_to_keep:
        ws_sales.append(list(row))

    # Append new rows (Date, sku, Product, Quantity, Unit_Price, Total, Payment_Method, Source)
    # Map parquet columns → Excel columns
    sku_map: dict[str, str] = {}
    prod_path = PARQUET_DIR / "products.parquet"
    if prod_path.exists():
        prods = pl.read_parquet(prod_path)
        if "full_name" in prods.columns and "sku" in prods.columns:
            sku_map = dict(zip(prods["full_name"].to_list(), prods["sku"].to_list()))

    appended = 0
    for row in new_sales.iter_rows(named=True):
        sku = sku_map.get(row["Product"], "")
        ws_sales.append([
            row["Date"],
            str(sku),
            row["Product"],
            round(float(row["Quantity"]), 3),
            round(float(row["Unit_Price"]), 2),
            round(float(row["Total"]), 2),
            row["Payment_Method"],
            row["Source"],
        ])
        appended += 1

    log.info("  📊 DailySales: +%d rows (source: %s)", appended, source_id)

    # ── Cashflow sheet ────────────────────────────────────────────────────────
    if cf_path.exists():
        cf = pl.read_parquet(cf_path)
        ws_cf = wb["Cashflow"]

        period_desc_prefix = f"Vendas {date_start}"
        new_cf_rows = cf.filter(
            pl.col("Description").str.starts_with(period_desc_prefix)
        ) if "Description" in cf.columns else pl.DataFrame()

        # Remove existing entries for this period
        cf_keep = []
        for i, row in enumerate(ws_cf.iter_rows(values_only=True)):
            if i == 0:
                continue
            if row and not str(row[3] or "").startswith(period_desc_prefix):
                cf_keep.append(row)

        ws_cf.delete_rows(2, ws_cf.max_row)
        for row in cf_keep:
            ws_cf.append(list(row))

        for row in new_cf_rows.iter_rows(named=True):
            ws_cf.append([
                row["Date"],
                row["Type"],
                row["Category"],
                row["Description"],
                round(float(row["Amount"]), 2),
                row["Payment_Method"],
            ])
        log.info("  📊 Cashflow: +%d entries", new_cf_rows.shape[0])

    # ── Save ──────────────────────────────────────────────────────────────────
    wb.save(str(EXCEL_MASTER))
    wb.close()
    log.info("  ✅ Excel Master saved")
    return True


# ══════════════════════════════════════════════════════════════════════════════
# MACOS NOTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def _notify(title: str, message: str, success: bool = True) -> None:
    """Send a native macOS notification (silent fail if not on macOS)."""
    try:
        sound = "Glass" if success else "Basso"
        script = (
            f'display notification "{message}" '
            f'with title "{title}" '
            f'subtitle "FulôFiló" '
            f'sound name "{sound}"'
        )
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, timeout=5
        )
    except Exception:
        pass  # Notifications are best-effort


# ══════════════════════════════════════════════════════════════════════════════
# GIT
# ══════════════════════════════════════════════════════════════════════════════

def _git_commit_push(archived: Path, date_start: str, date_end: str, dry_run: bool) -> bool:
    msg = f"auto: ingest sales {date_start}"
    if date_start != date_end:
        msg += f" → {date_end}"

    files_to_stage = [
        "data/parquet/",
        "data/excel/FuloFilo_Master.xlsx",
        str(archived.relative_to(ROOT)),
    ]

    ok = _run(["git", "add"] + files_to_stage, cwd=ROOT, dry_run=dry_run, label="git add")
    if not ok:
        return False

    commit_ok = _run(["git", "commit", "-m", msg], cwd=ROOT, dry_run=dry_run, label="git commit")
    if not commit_ok:
        log.info("  ℹ️  Nothing to commit")
        return True

    return _run(["git", "push", "origin", "main"], cwd=ROOT, dry_run=dry_run, label="git push")


# ══════════════════════════════════════════════════════════════════════════════
# CORE PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def process_file(path: Path, dry_run: bool) -> bool:
    log.info("━" * 60)
    log.info("📥 Processing: %s", path.name)

    # 1 — Validate filename
    m = FILENAME_RE.match(path.name)
    if not m:
        log.warning("  ⏭  Skipping — filename does not match pattern")
        return False
    date_start, date_end = m.group(1), m.group(2)
    source_id = path.stem

    # 2 — Validate internal columns
    if not _has_required_cols(path):
        log.error("  ❌ Invalid columns — file left for manual review")
        _notify("❌ FulôFiló Ingest Failed", f"Invalid columns: {path.name}", success=False)
        return False

    log.info("  📅 Period: %s → %s", date_start, date_end)

    # 3 — Duplicate guard
    if _already_ingested(source_id):
        log.warning("  ⚠️  Source '%s' already in parquet — re-ingesting (will replace)", source_id)

    # 4 — Run ingest (parquets + analytics)
    venv_python = ROOT / ".venv" / "bin" / "python"
    python = str(venv_python) if venv_python.exists() else sys.executable
    ingest_args = [python, str(INGEST), str(path)]
    if dry_run:
        ingest_args.append("--dry-run")

    ok = _run(ingest_args, cwd=ROOT, dry_run=False, label="etl/ingest.py")
    if not ok:
        log.error("  ❌ Ingest failed — file left in incoming/ for review")
        _notify("❌ FulôFiló Ingest Failed", f"Ingest error: {path.name}", success=False)
        return False

    # 5 — Sync Excel Master
    log.info("  📋 Syncing Excel Master...")
    _sync_excel_master(source_id, date_start, date_end, dry_run)

    # 6 — Archive
    archived = _archive(path, date_start, date_end, dry_run)
    if not archived:
        return False

    # 7 — Git commit + push
    pushed = _git_commit_push(archived, date_start, date_end, dry_run)

    # 8 — macOS notification
    if pushed:
        log.info("  🚀 Done — Streamlit Cloud redeploys in ~90 seconds")
        _notify(
            "✅ FulôFiló — Dashboard updated!",
            f"Sales {date_start} ingested. Live in ~90s."
        )
    else:
        _notify("⚠️ FulôFiló — Push failed", "Check logs/saleswatch.log", success=False)

    return pushed


def scan_and_process(dry_run: bool) -> int:
    if not INCOMING.exists():
        INCOMING.mkdir(parents=True)
        log.info("Created incoming folder: %s", INCOMING)

    candidates = sorted(INCOMING.glob("item-sales-summary-*.csv"))
    if not candidates:
        log.debug("No matching files in %s", INCOMING)
        return 0

    log.info("Found %d file(s) to process", len(candidates))
    ok_count = 0
    for f in candidates:
        if process_file(f, dry_run):
            ok_count += 1

    log.info("━" * 60)
    log.info("✅ Processed %d / %d file(s)", ok_count, len(candidates))
    return ok_count


def loop_mode(interval: int = 30) -> None:
    """Persistent daemon mode — polls every N seconds."""
    import time
    log.info("=" * 60)
    log.info("FulôFiló Sales Watcher — DAEMON MODE (poll every %ds)", interval)
    log.info("Watch folder: %s", INCOMING)
    log.info("=" * 60)
    while True:
        try:
            scan_and_process(dry_run=False)
        except Exception as exc:
            log.error("Unhandled error in scan loop: %s", exc)
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="FulôFiló — Sales Drop Watcher")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate — no files written, no git push")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("FulôFiló Sales Watcher  %s%s",
             datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             "  [DRY-RUN]" if args.dry_run else "")
    log.info("Watch folder: %s", INCOMING)
    log.info("=" * 60)

    scan_and_process(args.dry_run)


if __name__ == "__main__":
    main()
