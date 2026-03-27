#!/bin/bash
# ============================================================
#  🌺  FulôFiló Analytics Pro — One-Click Launcher
#  Double-click this file in Finder to start the system.
# ============================================================

PROJECT="/Users/eduardogiovannini/dev/products/FuloFilo"
VENV="$PROJECT/.venv/bin"
PORT=8501
URL="http://127.0.0.1:$PORT"
LOG="$PROJECT/logs/app.log"

mkdir -p "$PROJECT/logs"

clear
echo "╔══════════════════════════════════════════╗"
echo "║   🌺  FulôFiló Analytics Pro             ║"
echo "║   Iniciando sistema...                   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Check if already running ──────────────────────────────
if lsof -i :$PORT &>/dev/null; then
    echo "✅ Sistema já está rodando em $URL"
    echo "   Abrindo navegador..."
    open "$URL"
    exit 0
fi

# ── Check venv ────────────────────────────────────────────
if [ ! -f "$VENV/streamlit" ]; then
    echo "⚙️  Instalando dependências (primeira vez)..."
    cd "$PROJECT" && uv sync
fi

# ── Start Streamlit in background ─────────────────────────
echo "🚀 Iniciando Streamlit na porta $PORT..."
cd "$PROJECT"

nohup "$VENV/streamlit" run app/app.py \
    --server.port $PORT \
    --server.address 127.0.0.1 \
    --server.headless true \
    --theme.base dark \
    --theme.primaryColor "#52B788" \
    --theme.backgroundColor "#1A1A2E" \
    --theme.secondaryBackgroundColor "#16213E" \
    --theme.textColor "#E0E0E0" \
    > "$LOG" 2>&1 &

STREAMLIT_PID=$!
echo "   PID: $STREAMLIT_PID"
echo "   Log: $LOG"
echo ""

# ── Wait for server to be ready ───────────────────────────
echo "⏳ Aguardando servidor ficar pronto..."
MAX_WAIT=20
for i in $(seq 1 $MAX_WAIT); do
    if curl -s "$URL" &>/dev/null; then
        break
    fi
    printf "   %d/%d segundos...\r" "$i" "$MAX_WAIT"
    sleep 1
done

echo ""
echo "✅ Sistema pronto! Abrindo no navegador..."
echo ""
open "$URL"

echo "╔══════════════════════════════════════════╗"
echo "║  🌺 FulôFiló Analytics Pro está rodando ║"
echo "║  URL  : $URL          ║"
echo "║  PID  : $STREAMLIT_PID                         ║"
echo "║                                          ║"
echo "║  Para encerrar: feche esta janela ou     ║"
echo "║  execute: kill $STREAMLIT_PID                   ║"
echo "╚══════════════════════════════════════════╝"

# Keep terminal open so user can see status
wait $STREAMLIT_PID
