#!/usr/bin/env python3
"""
FulôFiló — Sales Drop Watcher
==============================
Triggered by launchd WatchPaths when a file lands in data/incoming/.

Workflow:
  1. Scan data/incoming/ for item-sales-summary-*.csv files
  2. Validate filename pattern + internal column signature
  3. Run etl/ingest.py → updates parquets + rebuilds analytics
  4. Archive file → data/raw/
  5. git commit + push → Streamlit Cloud redeploys

Usage (manual test):
    python scripts/sales_watcher.py
    python scripts/sales_watcher.py --dry-run
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
ROOT     = Path(__file__).resolve().parent.parent
INCOMING = ROOT / "data" / "incoming"
ARCHIVE  = ROOT / "data" / "raw"
LOGS_DIR = ROOT / "logs"
LOG_FILE = LOGS_DIR / "saleswatch.log"
INGEST   = ROOT / "etl" / "ingest.py"

# ── File pattern ──────────────────────────────────────────────────────────────
# Matches: item-sales-summary-2026-04-29-2026-04-29.csv  (any date)
FILENAME_RE = re.compile(
    r"^item-sales-summary-(\d{4}-\d{2}-\d{2})-(\d{4}-\d{2}-\d{2})\.csv$",
    re.IGNORECASE,
)

# Required columns (case-insensitive) — same as etl/ingest.py SALES_REQUIRED
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _has_required_cols(path: Path) -> bool:
    """Check that the CSV has the expected internal structure."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader, [])
        cols = {c.lower().strip() for c in header}
        missing = REQUIRED_COLS - cols
        if missing:
            log.warning("  Column check failed — missing: %s", missing)
            return False
        return True
    except Exception as exc:
        log.error("  Could not read %s: %s", path.name, exc)
        return False


def _run(cmd: list[str], cwd: Path, dry_run: bool, label: str) -> bool:
    """Run a subprocess. Returns True on success."""
    if dry_run:
        log.info("  [DRY-RUN] %s: %s", label, " ".join(str(c) for c in cmd))
        return True
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            log.info("  ✅ %s", label)
            if result.stdout.strip():
                for line in result.stdout.strip().splitlines():
                    log.info("     %s", line)
            return True
        else:
            log.error("  ❌ %s failed (exit %d)", label, result.returncode)
            if result.stderr.strip():
                log.error("     %s", result.stderr.strip()[:500])
            return False
    except subprocess.TimeoutExpired:
        log.error("  ❌ %s timed out (>120s)", label)
        return False
    except Exception as exc:
        log.error("  ❌ %s error: %s", label, exc)
        return False


def _archive(path: Path, date_start: str, date_end: str, dry_run: bool) -> Path | None:
    """Move processed file to data/raw/ with canonical name."""
    # Canonical name: item_sales_summary_YYYY-MM-DD_YYYY-MM-DD.csv
    canonical = f"item_sales_summary_{date_start}_{date_end}.csv"
    dest = ARCHIVE / canonical

    if dest.exists():
        # Backup with timestamp suffix to avoid silent overwrites
        ts = datetime.datetime.now().strftime("%H%M%S")
        dest = ARCHIVE / f"item_sales_summary_{date_start}_{date_end}_{ts}.csv"

    if dry_run:
        log.info("  [DRY-RUN] archive: %s → %s", path.name, dest.name)
        return dest

    try:
        shutil.move(str(path), str(dest))
        log.info("  📁 Archived → data/raw/%s", dest.name)
        return dest
    except Exception as exc:
        log.error("  ❌ Archive failed: %s", exc)
        return None


def _git_commit_push(archived: Path, date_start: str, date_end: str, dry_run: bool) -> bool:
    """Stage parquets + archived file, commit, push."""
    msg = f"auto: ingest sales {date_start}"
    if date_start != date_end:
        msg += f" → {date_end}"

    files_to_stage = [
        "data/parquet/",
        str(archived.relative_to(ROOT)),
    ]

    # Stage
    stage_ok = _run(
        ["git", "add"] + files_to_stage,
        cwd=ROOT, dry_run=dry_run, label="git add"
    )
    if not stage_ok:
        return False

    # Commit
    commit_ok = _run(
        ["git", "commit", "-m", msg],
        cwd=ROOT, dry_run=dry_run, label="git commit"
    )
    if not commit_ok:
        # Nothing to commit is fine (idempotent re-run)
        log.info("  ℹ️  Nothing to commit (already up-to-date)")
        return True

    # Push
    return _run(
        ["git", "push", "origin", "main"],
        cwd=ROOT, dry_run=dry_run, label="git push → Streamlit redeploy"
    )


# ── Core ──────────────────────────────────────────────────────────────────────

def process_file(path: Path, dry_run: bool) -> bool:
    """Full pipeline for one sales CSV. Returns True on success."""
    log.info("━" * 60)
    log.info("📥 Processing: %s", path.name)

    # 1 — Validate filename
    m = FILENAME_RE.match(path.name)
    if not m:
        log.warning("  ⏭  Skipping — filename does not match pattern")
        return False
    date_start, date_end = m.group(1), m.group(2)

    # 2 — Validate internal columns
    if not _has_required_cols(path):
        log.error("  ❌ Invalid column structure — file not processed")
        return False

    log.info("  📅 Period: %s → %s", date_start, date_end)

    # 3 — Run ingest
    # Use the project venv Python (has polars/duckdb); fall back to sys.executable
    venv_python = ROOT / ".venv" / "bin" / "python"
    python = str(venv_python) if venv_python.exists() else sys.executable
    ingest_args = [python, str(INGEST), str(path)]
    if dry_run:
        ingest_args.append("--dry-run")

    ok = _run(ingest_args, cwd=ROOT, dry_run=False, label="etl/ingest.py")
    if not ok:
        log.error("  ❌ Ingest failed — file left in incoming/ for manual review")
        return False

    # 4 — Archive
    archived = _archive(path, date_start, date_end, dry_run)
    if not archived:
        return False

    # 5 — Git commit + push
    pushed = _git_commit_push(archived, date_start, date_end, dry_run)
    if pushed:
        log.info("  🚀 Done — Streamlit Cloud will redeploy in ~90 seconds")
    return pushed


def scan_and_process(dry_run: bool) -> int:
    """Scan incoming/ and process all matching files. Returns count processed."""
    if not INCOMING.exists():
        INCOMING.mkdir(parents=True)
        log.info("Created incoming folder: %s", INCOMING)

    candidates = sorted(INCOMING.glob("item-sales-summary-*.csv"))
    if not candidates:
        log.debug("No matching files in %s — nothing to do", INCOMING)
        return 0

    log.info("Found %d file(s) to process", len(candidates))
    ok_count = 0
    for f in candidates:
        success = process_file(f, dry_run)
        if success:
            ok_count += 1

    log.info("━" * 60)
    log.info("✅ Processed %d / %d file(s)", ok_count, len(candidates))
    return ok_count


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="FulôFiló — Sales Drop Watcher")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate and simulate — no files written, no git push"
    )
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("FulôFiló Sales Watcher  %s%s",
             datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             "  [DRY-RUN]" if args.dry_run else "")
    log.info("Watch folder: %s", INCOMING)
    log.info("=" * 60)

    count = scan_and_process(args.dry_run)
    sys.exit(0 if count >= 0 else 1)


def loop_mode(interval: int = 30) -> None:
    """Run scan_and_process in a tight loop — for persistent daemon mode."""
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


if __name__ == "__main__":
    main()
