#!/bin/bash
# ============================================================
# FulôFiló — Excel master → Parquet sync
# ============================================================
set -euo pipefail

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$PROJECT/.venv/bin/python3"

if [ ! -x "$PY" ]; then
  echo "ERROR: venv missing. Run: cd $PROJECT && uv sync"
  exit 1
fi

cd "$PROJECT"
exec "$PY" "$PROJECT/scripts/sync_excel.py" "$@"
