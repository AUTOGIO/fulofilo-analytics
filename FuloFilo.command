#!/bin/bash
# ============================================================
#  🌺  FulôFiló Analytics Pro — One-Click Launcher
#  Double-click this file in Finder to start the system.
# ============================================================

# Resolve PROJECT relative to this script (portable — no hardcoded path)
PROJECT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$PROJECT/.venv/bin/python3"
STREAMLIT="$PROJECT/.venv/bin/streamlit"
PORT=8501
URL="http://127.0.0.1:$PORT"
LOG="$PROJECT/logs/app.log"

mkdir -p "$PROJECT/logs"

# Load the user's shell profile so uv is on PATH
# (.command files run non-interactive shells that miss ~/.local/bin etc.)
[ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env" 2>/dev/null
[ -f "$HOME/.zprofile" ]      && source "$HOME/.zprofile"      2>/dev/null
[ -f "$HOME/.zshrc"    ]      && source "$HOME/.zshrc"         2>/dev/null

clear
echo "╔══════════════════════════════════════════╗"
echo "║   🌺  FulôFiló Analytics Pro             ║"
echo "║   Iniciando sistema...                   ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "📂 Projeto: $PROJECT"
echo ""

# ── Check if already running ──────────────────────────────
if lsof -i :$PORT &>/dev/null; then
    echo "✅ Sistema já está rodando em $URL"
    echo "   Abrindo navegador..."
    open "$URL"
    exit 0
fi

# ── Heal broken venv (happens after path change) ──────────
# A venv is "broken" when the interpreter symlink points to a non-existent path
VENV_BROKEN=false
if [ ! -x "$PYTHON" ] || [ ! -x "$STREAMLIT" ]; then
    VENV_BROKEN=true
elif ! "$PYTHON" -c "import streamlit" &>/dev/null 2>&1; then
    VENV_BROKEN=true
fi

if [ "$VENV_BROKEN" = true ]; then
    echo "⚙️  Ambiente virtual ausente ou corrompido — recriando..."
    rm -rf "$PROJECT/.venv"
    cd "$PROJECT"
    if ! command -v uv &>/dev/null; then
        echo "⚙️  'uv' não encontrado — instalando automaticamente..."
        if curl -LsSf https://astral.sh/uv/install.sh | sh; then
            [ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env" 2>/dev/null
            export PATH="$HOME/.local/bin:$PATH"
        else
            echo "❌ Falha ao instalar 'uv'. Instale manualmente:"
            echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
            read -rp "   Pressione Enter para sair." _
            exit 1
        fi
    fi
    echo "   uv sync em andamento..."
    uv sync
    PYTHON="$PROJECT/.venv/bin/python3"
    STREAMLIT="$PROJECT/.venv/bin/streamlit"
    if [ ! -x "$PYTHON" ] || [ ! -x "$STREAMLIT" ]; then
        echo "❌ Ambiente virtual não ficou íntegro após uv sync."
        read -rp "   Pressione Enter para sair." _
        exit 1
    fi
    echo "   ✅ Dependências instaladas."
    echo ""
fi

# ── Open latest Excel report ──────────────────────────────
EXCEL=$(ls "$PROJECT/excel/FuloFilo_Report_"*.xlsx 2>/dev/null | sort | tail -1)
if [ -n "$EXCEL" ]; then
    echo "📊 Abrindo relatório Excel: $(basename "$EXCEL")"
    open "$EXCEL"
fi

# ── Start Streamlit in background ─────────────────────────
echo "🚀 Iniciando Streamlit na porta $PORT..."
cd "$PROJECT"

nohup "$STREAMLIT" run app/app.py \
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
MAX_WAIT=30
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
