#!/bin/bash
# ============================================================
# FulôFiló — Streamlit App Launcher
# Optimized for iMac M3, macOS 26.4, dark theme
# ============================================================
# Usage: ./scripts/launch_app.sh
# ============================================================

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
STREAMLIT="$PROJECT/.venv/bin/streamlit"

if [ ! -f "$STREAMLIT" ]; then
    echo "ERROR: Streamlit not found at $STREAMLIT"
    echo "  Run: cd $PROJECT && uv sync"
    exit 1
fi

cd "$PROJECT"

echo "🌺 Starting FulôFiló Analytics Pro..."
echo "   URL: http://127.0.0.1:8501"
echo "   Press Ctrl+C to stop"
echo ""

"$STREAMLIT" run app/app.py \
    --server.port 8501 \
    --server.address 127.0.0.1 \
    --server.headless false \
    --server.fileWatcherType auto \
    --theme.base dark \
    --theme.primaryColor "#52B788" \
    --theme.backgroundColor "#1A1A2E" \
    --theme.secondaryBackgroundColor "#16213E" \
    --theme.textColor "#E0E0E0"
