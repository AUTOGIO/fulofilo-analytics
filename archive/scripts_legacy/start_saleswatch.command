#!/bin/zsh
# FulôFiló — Start Sales Watcher (double-click to run)
# Double-click this file to start the background watcher.
# Keep the terminal window open — watcher runs every 30s.
# Close the window to stop it.

REPO="/Users/giovannini_nuovo/Documents/GitHub/FuloFilo"
PYTHON="$REPO/.venv/bin/python"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  FulôFiló Sales Watcher"
echo "  Drop zone: $REPO/data/incoming/"
echo "  Polling every 30 seconds..."
echo "  Press Ctrl+C to stop."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$REPO"
exec "$PYTHON" -c "
import sys
sys.path.insert(0, '$REPO/scripts')
import sales_watcher
sales_watcher.loop_mode(30)
"
