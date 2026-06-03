#!/usr/bin/env bash
# Start FulôFiló Guided Assistance only (port 8502) and open in browser.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GUIDE_PORT=8502
GUIDE_URL="http://127.0.0.1:$GUIDE_PORT"
LOG="$ROOT/logs/guided_assistance.log"

[ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env" 2>/dev/null || true
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

mkdir -p "$ROOT/logs"

if ! command -v uv >/dev/null 2>&1; then
  curl -fsSL https://astral.sh/uv/install.sh | sh
  [ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env" 2>/dev/null || true
  export PATH="$HOME/.local/bin:$PATH"
fi

STREAMLIT="$ROOT/.venv/bin/streamlit"
if [ ! -x "$STREAMLIT" ]; then
  (cd "$ROOT" && uv sync)
  STREAMLIT="$ROOT/.venv/bin/streamlit"
fi

if lsof -i ":$GUIDE_PORT" &>/dev/null; then
  echo "Assistente já rodando em $GUIDE_URL"
  open "$GUIDE_URL"
  exit 0
fi

cd "$ROOT"
nohup "$STREAMLIT" run tools/guided_assistance/app.py \
  --server.port "$GUIDE_PORT" \
  --server.address 127.0.0.1 \
  --server.headless true \
  --theme.base light \
  >"$LOG" 2>&1 &

for i in $(seq 1 30); do
  if curl -sf "$GUIDE_URL" >/dev/null 2>&1; then
    open "$GUIDE_URL"
    echo "Assistente FulôFiló aberto: $GUIDE_URL"
    exit 0
  fi
  sleep 1
done

echo "Assistente demorou a iniciar. Veja: $LOG" >&2
exit 1
