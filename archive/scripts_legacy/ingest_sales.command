#!/bin/zsh
# FulôFiló — Ingest Sales (double-click from Finder)
# ──────────────────────────────────────────────────
# 1. Save your item-sales-summary-*.csv to data/incoming/
# 2. Double-click this file
# 3. Dashboard updates in ~90 seconds
# ──────────────────────────────────────────────────

REPO="/Users/giovannini_nuovo/Documents/GitHub/FuloFilo"
PYTHON="$REPO/.venv/bin/python"

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
