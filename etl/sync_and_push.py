"""
FulôFiló — Sync & Push
======================
Stage changed data/app files → git commit → push → Streamlit redeploys.

Usage:
    python etl/sync_and_push.py                          # push all changes
    python etl/sync_and_push.py --message "my note"      # custom commit msg
    python etl/sync_and_push.py --dry-run                # validate, no push
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# Files tracked for staging
TRACKED = [
    # ── App core ──────────────────────────────────────────────────────────────
    "app/app.py",
    "app/db.py",
    "app/components/sidebar.py",
    "app/components/hud.py",
    "app/pages/01_abc_analysis.py",
    "app/pages/02_margin_matrix.py",
    "app/pages/03_inventory.py",
    "app/pages/04_daily_ops.py",
    "app/pages/05_categories.py",
    "app/pages/06_export_excel.py",
    "app/utils/inventory_ops.py",
    "app/utils/reorder_engine.py",
    "app/utils/fixed_costs.py",
    "app/utils/sales_ops.py",
    # ── ETL ───────────────────────────────────────────────────────────────────
    "etl/sync_and_push.py",
    "etl/ingest_march_april_2026.py",
    "etl/build_catalog.py",
    # ── Docs ──────────────────────────────────────────────────────────────────
    "docs/README.md",
    "docs/DATA_DICTIONARY.md",
    "docs/USER_GUIDE.md",
    "docs/AUDIT_REPORT.md",
    "docs/SHORTCUTS.md",
    # ── Parquet data ──────────────────────────────────────────────────────────
    "data/parquet/products.parquet",
    "data/parquet/products_2026.parquet",
    "data/parquet/products_2026_03.parquet",
    "data/parquet/products_2026_04.parquet",
    "data/parquet/products_2024.parquet",
    "data/parquet/inventory.parquet",
    "data/parquet/daily_sales.parquet",
    "data/parquet/cashflow.parquet",
    "data/parquet/profit_report.parquet",
    "data/parquet/quantity_report.parquet",
    "data/parquet/revenue_report.parquet",
    # ── Raw data ──────────────────────────────────────────────────────────────
    "data/raw/dashboard_data.json",
    "data/raw/dashboard_data_2026.json",
    "data/raw/product_catalog.csv",
    "data/raw/product_catalog_categorized.csv",
    "data/raw/vendas_marco_26.csv",
    "data/raw/vendas_abril_26.csv",
    "data/raw/custos_fixos/custos_fixos.txt",
]


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(BASE), capture_output=True, text=True, check=check)


def log(msg: str) -> None:
    print(msg, flush=True)


def push(message: str = "manual sync via dashboard", dry_run: bool = False) -> bool:
    log("=" * 50)
    log("FulôFiló — Sync & Push")
    log("=" * 50)

    # 1. Stage tracked files that exist
    to_add = [f for f in TRACKED if (BASE / f).exists()]
    # Also stage any vendas_*.csv in data/raw/
    for csv in (BASE / "data" / "raw").glob("vendas_*.csv"):
        rel = str(csv.relative_to(BASE))
        if rel not in to_add:
            to_add.append(rel)

    run(["git", "add"] + to_add, check=False)

    # 2. Check if anything is staged
    status = run(["git", "status", "--porcelain"], check=False)
    staged = [l for l in status.stdout.splitlines() if l.strip()]
    if not staged:
        log("ℹ️  Nothing to commit — already up to date.")
        return True

    log(f"📝 {len(staged)} file(s) changed")

    commit_msg = f"data: {message} [{datetime.now().strftime('%Y-%m-%d %H:%M')}]"

    if dry_run:
        log(f"[DRY RUN] Would commit: {commit_msg}")
        log("[DRY RUN] Would push to origin main")
        return True

    # 3. Commit
    r = run(["git", "commit", "-m", commit_msg], check=False)
    if r.returncode != 0 and "nothing to commit" not in r.stdout:
        log(f"❌ Commit failed:\n{r.stderr[:300]}")
        return False
    log(f"✅ Committed: {commit_msg}")

    # 4. Ensure HTTPS remote (self-healing — SSH has no key registered)
    run(["git", "remote", "set-url", "origin",
         "https://github.com/AUTOGIO/fulofilo-analytics.git"], check=False)

    # 5. Push (HTTPS — uses macOS Keychain credentials)
    log("🚀 Pushing to GitHub...")
    r = run(["git", "push", "origin", "main"], check=False)
    if r.returncode != 0:
        log(f"❌ Push failed:\n{r.stderr[:300]}")
        return False

    log("✅ Pushed! Streamlit Cloud redeploys in ~60s")
    log("🌐 https://autogio-fulofilo.streamlit.app/")
    log("=" * 50)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FulôFiló sync & push")
    parser.add_argument("--message", type=str, default="manual sync via dashboard")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ok = push(message=args.message, dry_run=args.dry_run)
    sys.exit(0 if ok else 1)
