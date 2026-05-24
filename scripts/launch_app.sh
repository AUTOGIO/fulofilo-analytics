#!/bin/bash
# ============================================================
# FulôFiló AI — Retail Operations Terminal Launcher
# Official institutional dashboard for local Excel-first operations.
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

echo "Starting FulôFiló AI Retail Operations Terminal..."
echo "   URL: http://127.0.0.1:8501"
echo "   Press Ctrl+C to stop"
echo ""

"$STREAMLIT" run app/app.py \
    --server.port 8501 \
    --server.address 127.0.0.1 \
    --server.headless false \
    --server.fileWatcherType auto \
    --theme.base dark \
    --theme.primaryColor "#35D07F" \
    --theme.backgroundColor "#050809" \
    --theme.secondaryBackgroundColor "#0B1515" \
    --theme.textColor "#DCE6E3"
