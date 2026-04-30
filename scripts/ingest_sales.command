#!/bin/zsh
# FulôFiló — Ingest Sales
# ─────────────────────────────────────────────────────────────────────────────
# Drop item-sales-summary-*.csv into data/incoming/ then double-click this file.
#
# • If iTerm2 is installed  → opens a FulôFiló-profile window in iTerm2
# • Otherwise               → runs inline in the current terminal
# ─────────────────────────────────────────────────────────────────────────────

REPO="/Users/giovannini_nuovo/Documents/GitHub/FuloFilo"
PYTHON="$REPO/.venv/bin/python"
PROFILE="FulôFiló"   # iTerm2 dynamic profile (installed by setup_iterm_profile.sh)

# ── Already inside iTerm2 → do the actual work ───────────────────────────────
if [[ "$TERM_PROGRAM" == "iTerm.app" ]]; then
    cd "$REPO"

    echo ""
    echo "  ┌─────────────────────────────────────────┐"
    echo "  │        FulôFiló — Sales Ingest          │"
    echo "  └─────────────────────────────────────────┘"
    echo ""

    "$PYTHON" scripts/sales_watcher.py

    echo ""
    echo "  Pressione qualquer tecla para fechar..."
    read -k1
    exit 0
fi

# ── iTerm2 installed → re-launch self inside an iTerm2 window ────────────────
if [[ -d "/Applications/iTerm.app" ]]; then
    SELF="${0:A}"   # absolute path to this script
    osascript <<APPLESCRIPT
tell application "iTerm2"
    activate
    try
        set newWin to (create window with profile "$PROFILE")
    on error
        set newWin to (create window with default profile)
    end try
    delay 0.4
    tell current session of newWin
        write text "zsh '$SELF'"
    end tell
end tell
APPLESCRIPT
    exit 0
fi

# ── Fallback: run inline (no iTerm2 found) ───────────────────────────────────
cd "$REPO"

echo ""
echo "  ┌─────────────────────────────────────────┐"
echo "  │        FulôFiló — Sales Ingest          │"
echo "  └─────────────────────────────────────────┘"
echo ""

"$PYTHON" scripts/sales_watcher.py

echo ""
echo "  Pressione qualquer tecla para fechar..."
read -k1
