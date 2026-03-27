#!/bin/bash
# ============================================================
# FulôFiló — Full Data Refresh Pipeline
# ============================================================
# Usage:
#   chmod +x scripts/refresh_data.sh
#   ./scripts/refresh_data.sh
#
# Triggered automatically by macOS Shortcut when a new
# Eleve export is dropped into ~/Documents/FuloFilo_Inbox/
# ============================================================

set -euo pipefail

PROJECT="/Users/eduardogiovannini/dev/products/FuloFilo"
VENV="$PROJECT/.venv/bin/python3"
LOG_FILE="$PROJECT/logs/refresh.log"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

mkdir -p "$PROJECT/logs"

log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

# ── Preflight checks ──────────────────────────────────────
log "======================================================"
log "FulôFiló data refresh started"
log "======================================================"

if [ ! -d "$PROJECT" ]; then
    log "ERROR: Project directory not found: $PROJECT"
    exit 1
fi

if [ ! -f "$VENV" ]; then
    log "ERROR: Python venv not found at $VENV"
    log "  Run: cd $PROJECT && uv sync"
    exit 1
fi

cd "$PROJECT"

# ── Check for inbox file (optional — skip if not present) ──
INBOX="$HOME/Documents/FuloFilo_Inbox"
if [ -d "$INBOX" ]; then
    LATEST=$(ls -t "$INBOX"/*.json 2>/dev/null | head -1 || echo "")
    if [ -n "$LATEST" ]; then
        log "Found inbox file: $LATEST — moving to data/raw/"
        cp "$LATEST" "$PROJECT/data/raw/dashboard_data.json"
        mv "$LATEST" "$INBOX/processed/"
        log "Inbox file moved to processed/"
    fi
fi

# ── Step 1: Build catalog from raw text files ─────────────
log "Step 1/3: build_catalog.py"
"$VENV" etl/build_catalog.py >> "$LOG_FILE" 2>&1 && log "  ✅ build_catalog OK" || {
    log "  ❌ build_catalog FAILED"; exit 1
}

# ── Step 2: Ingest Eleve Vendas JSON export ───────────────
log "Step 2/3: ingest_eleve.py"
"$VENV" etl/ingest_eleve.py >> "$LOG_FILE" 2>&1 && log "  ✅ ingest_eleve OK" || {
    log "  ❌ ingest_eleve FAILED"; exit 1
}

# ── Step 3: Categorize products ───────────────────────────
log "Step 3/3: categorize_products.py"
"$VENV" etl/categorize_products.py >> "$LOG_FILE" 2>&1 && log "  ✅ categorize_products OK" || {
    log "  ❌ categorize_products FAILED"; exit 1
}

log "======================================================"
log "Refresh complete ✅"
log "======================================================"

# macOS notification
osascript -e 'display notification "Dados atualizados com sucesso ✅" with title "FulôFiló Analytics"' 2>/dev/null || true
