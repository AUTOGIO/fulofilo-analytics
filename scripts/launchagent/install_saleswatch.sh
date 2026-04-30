#!/bin/zsh
# ──────────────────────────────────────────────────────────────────────────────
# FulôFiló — Install Sales Drop Watcher
# Copies the plist to ~/Library/LaunchAgents/ and loads it.
# Usage: bash scripts/launchagent/install_saleswatch.sh
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

LABEL="com.fulofilo.saleswatch"
PLIST_SRC="$(cd "$(dirname "$0")" && pwd)/${LABEL}.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/${LABEL}.plist"
INCOMING="$(cd "$(dirname "$0")/../.." && pwd)/data/incoming"
LOGS="$(cd "$(dirname "$0")/../.." && pwd)/logs"

echo "FulôFiló — Sales Drop Watcher Installer"
echo "========================================"

# 1 — Create folders
mkdir -p "$INCOMING"
mkdir -p "$LOGS"
echo "✅ Folders ready"
echo "   Drop zone : $INCOMING"
echo "   Logs      : $LOGS"

# 2 — Unload existing agent if already installed
if launchctl list | grep -q "$LABEL" 2>/dev/null; then
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    echo "✅ Unloaded existing agent"
fi

# 3 — Copy plist
cp "$PLIST_SRC" "$PLIST_DEST"
echo "✅ Plist installed → $PLIST_DEST"

# 4 — Load agent
launchctl load "$PLIST_DEST"
echo "✅ Agent loaded and active"

# 5 — Verify
if launchctl list | grep -q "$LABEL"; then
    echo ""
    echo "🟢 Watcher is ACTIVE"
    echo ""
    echo "  How to use:"
    echo "  1. Save any 'item-sales-summary-YYYY-MM-DD-YYYY-MM-DD.csv' to:"
    echo "     $INCOMING"
    echo "  2. The pipeline runs automatically (~10s later)"
    echo "  3. Streamlit redeploys in ~90 seconds"
    echo ""
    echo "  Watch live: tail -f $LOGS/saleswatch.log"
    echo "  Test now:   python scripts/sales_watcher.py --dry-run"
    echo ""
else
    echo "❌ Agent load failed — check:"
    echo "   plutil -lint $PLIST_DEST"
fi
