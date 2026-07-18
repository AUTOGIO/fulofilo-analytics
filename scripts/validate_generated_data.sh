#!/usr/bin/env bash
# ============================================================
# FulôFiló — Validate generated read models after sync
# ============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$REPO_ROOT/.venv/bin/python3"

EXCEL_MASTER="$REPO_ROOT/data/excel/FuloFilo_Master.xlsx"
PARQUET_DIR="$REPO_ROOT/data/parquet"
DUCKDB_FILE="$REPO_ROOT/data/fulofilo.duckdb"
STATUS_JSON="$REPO_ROOT/data/excel/source_sync_status.json"

CANONICAL_PARQUETS=(
  cashflow
  daily_sales
  inventory
  products
  profit_report
  quantity_report
  revenue_report
)

log() {
  echo "[validate] $*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

warn() {
  log "WARN: $*"
}

cd "$REPO_ROOT"

if [[ ! -x "$PY" ]]; then
  fail "venv missing. Run: cd $REPO_ROOT && uv sync"
fi

log "Checking Excel master..."
if [[ ! -f "$EXCEL_MASTER" ]]; then
  fail "Excel master not found: $EXCEL_MASTER"
fi
if [[ ! -s "$EXCEL_MASTER" ]]; then
  fail "Excel master is empty: $EXCEL_MASTER"
fi
log "OK — Excel master exists ($(wc -c < "$EXCEL_MASTER" | tr -d ' ') bytes)"

log "Checking parquet directory..."
if [[ ! -d "$PARQUET_DIR" ]]; then
  fail "Parquet directory not found: $PARQUET_DIR"
fi
parquet_count="$(find "$PARQUET_DIR" -maxdepth 1 -name '*.parquet' | wc -l | tr -d ' ')"
if [[ "$parquet_count" -eq 0 ]]; then
  fail "Parquet directory is empty: $PARQUET_DIR"
fi
log "OK — parquet directory has $parquet_count file(s)"

log "Checking for zero-byte parquet files..."
zero_byte="$(find "$PARQUET_DIR" -maxdepth 1 -name '*.parquet' -size 0 -print || true)"
if [[ -n "$zero_byte" ]]; then
  fail "Zero-byte parquet files found:\n$zero_byte"
fi
log "OK — no zero-byte parquet files"

log "Checking canonical parquet files..."
for name in "${CANONICAL_PARQUETS[@]}"; do
  file="$PARQUET_DIR/${name}.parquet"
  if [[ ! -f "$file" ]]; then
    fail "Missing canonical parquet: $file"
  fi
  if [[ ! -s "$file" ]]; then
    fail "Canonical parquet is empty: $file"
  fi
  "$PY" -c "
import polars as pl
pl.read_parquet('${file}')
" || fail "Cannot read parquet: $file"
  log "OK — ${name}.parquet"
done

if [[ -f "$STATUS_JSON" ]]; then
  log "Checking source_sync_status.json..."
  ok_value="$("$PY" -c "
import json
from pathlib import Path
data = json.loads(Path('${STATUS_JSON}').read_text(encoding='utf-8'))
print('true' if data.get('ok') else 'false')
")"
  if [[ "$ok_value" != "true" ]]; then
    fail "source_sync_status.json reports ok=false"
  fi
  log "OK — source_sync_status.json ok=true"
else
  warn "source_sync_status.json not found (optional locally)"
fi

if [[ -f "$DUCKDB_FILE" ]]; then
  if [[ ! -s "$DUCKDB_FILE" ]]; then
    fail "DuckDB file exists but is empty: $DUCKDB_FILE"
  fi
  log "OK — DuckDB file exists ($(wc -c < "$DUCKDB_FILE" | tr -d ' ') bytes)"
else
  warn "DuckDB file not found (dashboard bootstraps at runtime): $DUCKDB_FILE"
fi

log "All validation checks passed."
