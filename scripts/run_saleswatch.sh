#!/bin/zsh
# FulôFiló — Sales Watcher launcher (called by launchd)
# Using a shell wrapper is more reliable than calling Python directly from launchd.

REPO="/Users/giovannini_nuovo/Documents/GitHub/FuloFilo"
PYTHON="$REPO/.venv/bin/python"
SCRIPT="$REPO/scripts/sales_watcher.py"
LOG="$REPO/logs/saleswatch.log"

mkdir -p "$REPO/logs"
touch "$LOG"

exec "$PYTHON" "$SCRIPT" >> "$LOG" 2>&1
