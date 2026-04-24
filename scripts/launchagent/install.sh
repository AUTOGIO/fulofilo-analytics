#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# FulôFiló — LaunchAgent Installer
# Installs the daily auto-sync agent on macOS.
# Run from project root: bash scripts/launchagent/install.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

PLIST_SRC="$(cd "$(dirname "$0")" && pwd)/com.fulofilo.autosync.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.fulofilo.autosync.plist"
LOGS_DIR="$(cd "$(dirname "$0")/../.." && pwd)/logs"

echo ""
echo "🔧 FulôFiló — LaunchAgent Installer"
echo "────────────────────────────────────"

# Create logs dir
mkdir -p "$LOGS_DIR"
echo "  ✅ Logs dir: $LOGS_DIR"

# Copy plist
cp "$PLIST_SRC" "$PLIST_DST"
echo "  ✅ Plist installed → $PLIST_DST"

# Unload if already running
launchctl unload "$PLIST_DST" 2>/dev/null || true

# Load new agent
launchctl load "$PLIST_DST"
echo "  ✅ LaunchAgent loaded"

echo ""
echo "  ⏰ Schedule: daily at 07:00 AM"
echo "  📋 Logs: $LOGS_DIR/autosync_stdout.log"
echo ""
echo "  Commands:"
echo "    tail -f $LOGS_DIR/autosync_stdout.log     # view live logs"
echo "    launchctl start com.fulofilo.autosync      # run now manually"
echo "    launchctl unload $PLIST_DST               # disable"
echo ""
echo "  ✅ Done — next auto-sync: tomorrow 07:00 AM"
