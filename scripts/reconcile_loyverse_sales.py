#!/usr/bin/env python3
"""Reconcile Excel DailySales with the latest Loyverse period export."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.utils.loyverse_reconciliation import reconcile_loyverse_period  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Align FuloFilo_Master DailySales with a Loyverse period anchor CSV.",
    )
    parser.add_argument(
        "--anchor",
        type=Path,
        default=None,
        help="Path to item-sales-summary CSV. Defaults to latest file in data/incoming or data/raw.",
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Update Excel only; skip scripts/sync_excel.sh.",
    )
    args = parser.parse_args()

    result = reconcile_loyverse_period(anchor_path=args.anchor, sync_after=not args.no_sync)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    if result.skipped:
        return 0
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
