"""
FulôFiló — Auto-Update Pipeline
================================
Ingest new CSVs → rebuild parquets → git commit → push → Streamlit redeploys.

Usage:
    python etl/sync_and_push.py                     # run once
    python etl/sync_and_push.py --watch             # watch data/raw/ for new CSVs
    python etl/sync_and_push.py --csv path/to/file  # ingest a specific CSV first
    python etl/sync_and_push.py --dry-run           # validate without pushing

Streamlit Cloud auto-redeploys within ~60s of each push to main.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW  = BASE / "data" / "raw"
OUT  = BASE / "data" / "parquet"
LOGS = BASE / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

# Files that trigger a re-push when changed
TRACKED_DATA = [
    "data/parquet/products.parquet",
    "data/parquet/products_2024.parquet",
    "data/parquet/products_2026.parquet",
    "data/parquet/inventory.parquet",
    "data/raw/dashboard_data.json",
    "data/raw/dashboard_data_2026.json",
    "data/raw/product_catalog.csv",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    ts  = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOGS / "sync.log", "a") as f:
        f.write(line + "\n")


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(BASE), capture_output=True, text=True, check=check)


def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.md5(path.read_bytes()).hexdigest()


def snapshot_hashes() -> dict[str, str]:
    return {f: file_hash(BASE / f) for f in TRACKED_DATA}


def data_changed(before: dict, after: dict) -> bool:
    return before != after


def detect_new_csvs(watch_dir: Path) -> list[Path]:
    """Return CSVs in watch_dir whose names start with 'vendas_'."""
    return sorted(watch_dir.glob("vendas_*.csv"))


# ── Pipeline steps ────────────────────────────────────────────────────────────

def step_ingest_csv(csv_path: Path) -> bool:
    """Run the ingest_march_april_2026 script for a given CSV (if applicable)."""
    # Copy CSV to data/raw/ so the ingest script picks it up
    dest = RAW / csv_path.name
    if dest != csv_path:
        shutil.copy2(csv_path, dest)
        log(f"  📥 Copied {csv_path.name} → data/raw/")

    log("  🔄 Running ingest_march_april_2026.py ...")
    result = run([sys.executable, str(BASE / "etl" / "ingest_march_april_2026.py")], check=False)
    if result.returncode != 0:
        log(f"  ⚠️  Ingest error:\n{result.stderr[:400]}")
        return False
    log("  ✅ Ingest complete")
    return True


def step_build_catalog() -> bool:
    log("  🔄 Rebuilding parquets (build_catalog.py) ...")
    result = run([sys.executable, str(BASE / "etl" / "build_catalog.py")], check=False)
    if result.returncode != 0:
        log(f"  ⚠️  Build error:\n{result.stderr[:400]}")
        return False
    log("  ✅ Parquets rebuilt")
    return True


def step_git_push(message: str, dry_run: bool = False) -> bool:
    """Stage data files, commit, and push to origin/main."""
    # Stage only tracked data files (not code changes)
    files_to_add = [f for f in TRACKED_DATA if (BASE / f).exists()]
    # Also add new CSV files in data/raw/
    for csv in RAW.glob("vendas_*.csv"):
        rel = str(csv.relative_to(BASE))
        if rel not in files_to_add:
            files_to_add.append(rel)

    run(["git", "add"] + files_to_add)

    # Check if there's anything to commit
    status = run(["git", "status", "--porcelain"] + files_to_add, check=False)
    staged = [l for l in status.stdout.splitlines() if l.strip()]
    if not staged:
        log("  ℹ️  Nothing changed — skipping commit")
        return True

    log(f"  📝 Committing {len(staged)} changed file(s)...")
    commit_msg = f"data: {message} [{datetime.now().strftime('%Y-%m-%d %H:%M')}]"

    if dry_run:
        log(f"  [DRY RUN] Would commit: {commit_msg}")
        log(f"  [DRY RUN] Would push to origin main")
        return True

    r = run(["git", "commit", "-m", commit_msg], check=False)
    if r.returncode != 0 and "nothing to commit" not in r.stdout:
        log(f"  ⚠️  Commit failed: {r.stderr[:200]}")
        return False

    log("  🚀 Pushing to GitHub (origin main)...")
    # Use HTTPS remote temporarily — SSH key (id_ed25519_autogio) is not registered on GitHub
    run(["git", "remote", "set-url", "origin", "https://github.com/AUTOGIO/fulofilo-analytics.git"], check=False)
    r = run(["git", "push", "origin", "main"], check=False)
    run(["git", "remote", "set-url", "origin", "git@github.com:AUTOGIO/fulofilo-analytics.git"], check=False)
    if r.returncode != 0:
        log(f"  ⚠️  Push failed: {r.stderr[:300]}")
        return False

    log("  ✅ Pushed! Streamlit Cloud will redeploy in ~60s")
    log(f"  🌐 https://autogio-fulofilo.streamlit.app/")
    return True


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_pipeline(
    csv_path:  Path | None = None,
    dry_run:   bool = False,
    message:   str  = "auto sync",
) -> bool:
    log("=" * 55)
    log("FulôFiló — Auto-Update Pipeline")
    log("=" * 55)

    before = snapshot_hashes()

    # 1. Ingest new CSV (optional)
    if csv_path:
        ok = step_ingest_csv(csv_path)
        if not ok:
            log("❌ Ingest failed — aborting")
            return False

    # 2. Rebuild parquets
    ok = step_build_catalog()
    if not ok:
        log("❌ Build failed — aborting")
        return False

    after = snapshot_hashes()

    # 3. Push if data changed
    if not data_changed(before, after) and not csv_path:
        log("ℹ️  Data unchanged — nothing to deploy")
        return True

    ok = step_git_push(message, dry_run=dry_run)
    log("=" * 55)
    log("✅ Pipeline complete" if ok else "❌ Pipeline finished with errors")
    return ok


def watch_mode(watch_dir: Path, interval_secs: int = 30, dry_run: bool = False) -> None:
    """Poll watch_dir every `interval_secs` seconds for new CSV files."""
    log(f"👁  Watch mode — polling {watch_dir} every {interval_secs}s")
    log("    Press Ctrl+C to stop\n")

    seen: set[str] = {f.name for f in detect_new_csvs(watch_dir)}
    log(f"    Baseline: {len(seen)} CSV(s) already present")

    while True:
        time.sleep(interval_secs)
        current = {f.name: f for f in detect_new_csvs(watch_dir)}
        new_files = [f for name, f in current.items() if name not in seen]

        if new_files:
            for csv_path in new_files:
                log(f"\n🆕 New CSV detected: {csv_path.name}")
                ok = run_pipeline(
                    csv_path=csv_path,
                    dry_run=dry_run,
                    message=f"ingest {csv_path.stem}",
                )
                if ok:
                    seen.add(csv_path.name)
        else:
            log(f"  [{datetime.now().strftime('%H:%M:%S')}] No new files — waiting...")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FulôFiló auto-update pipeline")
    parser.add_argument("--csv",     type=Path, default=None,
                        help="Path to new CSV to ingest before rebuilding")
    parser.add_argument("--watch",   action="store_true",
                        help="Watch data/raw/ for new CSV files continuously")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run ETL but skip git commit/push")
    parser.add_argument("--interval", type=int, default=30,
                        help="Poll interval in seconds for --watch mode (default: 30)")
    parser.add_argument("--message",  type=str, default="auto sync",
                        help="Custom git commit message")
    args = parser.parse_args()

    if args.watch:
        watch_mode(RAW, interval_secs=args.interval, dry_run=args.dry_run)
    else:
        ok = run_pipeline(
            csv_path=args.csv,
            dry_run=args.dry_run,
            message=args.message,
        )
        sys.exit(0 if ok else 1)
