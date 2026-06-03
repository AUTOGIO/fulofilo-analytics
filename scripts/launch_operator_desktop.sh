#!/usr/bin/env bash
# Launch Streamlit dashboard, macOS FF Terminal, and guided assistance (non-developer).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STREAMLIT_PORT=8501
GUIDE_PORT=8502
STREAMLIT_URL="http://127.0.0.1:$STREAMLIT_PORT"
GUIDE_URL="http://127.0.0.1:$GUIDE_PORT"
LOG_DIR="$ROOT/logs"
STREAMLIT_LOG="$LOG_DIR/streamlit_operator.log"
GUIDE_LOG="$LOG_DIR/guided_assistance.log"
MAC_BIN="$ROOT/macos/FuloFiloTerminal/.build/release/FuloFiloTerminal"

[ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env" 2>/dev/null || true
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

mkdir -p "$LOG_DIR"

if [ ! -f "$ROOT/data/.operator_setup_complete" ]; then
  echo "First run: bootstrapping installation..."
  FULOFILO_REPO="$ROOT" bash "$ROOT/scripts/operator_bootstrap.sh"
fi

STREAMLIT="$ROOT/.venv/bin/streamlit"
PYTHON="$ROOT/.venv/bin/python3"
if [ ! -x "$STREAMLIT" ]; then
  echo "Running uv sync..."
  (cd "$ROOT" && uv sync)
fi

wait_for_url() {
  local url=$1 max=${2:-45}
  for i in $(seq 1 "$max"); do
    if curl -sf "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

start_streamlit() {
  if lsof -i ":$STREAMLIT_PORT" &>/dev/null; then
    echo "Streamlit already on $STREAMLIT_PORT"
    return 0
  fi
  echo "Starting Streamlit dashboard..."
  cd "$ROOT"
  nohup "$STREAMLIT" run app/app.py \
    --server.port "$STREAMLIT_PORT" \
    --server.address 127.0.0.1 \
    --server.headless true \
    --theme.base dark \
    --theme.primaryColor "#35D07F" \
    --theme.backgroundColor "#050809" \
    --theme.secondaryBackgroundColor "#0B1515" \
    --theme.textColor "#DCE6E3" \
    >"$STREAMLIT_LOG" 2>&1 &
  wait_for_url "$STREAMLIT_URL" 40 || echo "Warning: Streamlit slow to start — check $STREAMLIT_LOG"
}

start_guided_assistance() {
  if lsof -i ":$GUIDE_PORT" &>/dev/null; then
    echo "Guided assistance already on $GUIDE_PORT"
    return 0
  fi
  echo "Starting guided assistance..."
  cd "$ROOT"
  nohup "$STREAMLIT" run tools/guided_assistance/app.py \
    --server.port "$GUIDE_PORT" \
    --server.address 127.0.0.1 \
    --server.headless true \
    --theme.base light \
    >"$GUIDE_LOG" 2>&1 &
  wait_for_url "$GUIDE_URL" 30 || echo "Warning: Guide slow to start — check $GUIDE_LOG"
}

start_macos_terminal() {
  if ! command -v swift >/dev/null 2>&1; then
    echo "Skipping FF Terminal: install Xcode Command Line Tools (xcode-select --install)"
    return 0
  fi
  if [ ! -x "$MAC_BIN" ]; then
    bash "$ROOT/scripts/build_macos_terminal.sh" || return 0
  fi
  if [ -x "$MAC_BIN" ]; then
    echo "Opening FF Terminal (native macOS)..."
    nohup "$MAC_BIN" >/dev/null 2>&1 &
  fi
}

start_streamlit
start_macos_terminal
start_guided_assistance

sleep 2
open "$STREAMLIT_URL"
sleep 1
open "$GUIDE_URL"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  FulôFiló — painéis abertos                              ║"
echo "║  Dashboard web : $STREAMLIT_URL              ║"
echo "║  Assistente    : $GUIDE_URL              ║"
echo "║  FF Terminal   : app nativa macOS (se compilou)           ║"
echo "╚══════════════════════════════════════════════════════════╝"
