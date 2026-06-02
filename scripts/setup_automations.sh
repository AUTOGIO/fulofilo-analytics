#!/usr/bin/env bash
# Bootstrap Loyverse + Rede automations inside fulofilo-analytics (portable after git clone).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOYVERSE_ROOT="${LOYVERSE_DATA_ROOT:-$ROOT/automations/loyverse-data}"
REDE_ROOT="${REDE_AUTOMATION_ROOT:-$ROOT/automations/rede-automation}"

mkdir -p "$LOYVERSE_ROOT/raw" "$LOYVERSE_ROOT/processed" "$LOYVERSE_ROOT/logs" "$LOYVERSE_ROOT/chrome-profile"
mkdir -p "$REDE_ROOT/logs/debug" "$REDE_ROOT/.browser-profile"

echo "Loyverse data root: $LOYVERSE_ROOT"
echo "Rede automation root: $REDE_ROOT"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found. Install Node.js (https://nodejs.org/) for Rede automation." >&2
  exit 1
fi

(
  cd "$REDE_ROOT"
  npm install
  npx playwright install chromium
)

if [[ -x "$ROOT/.venv/bin/python3" ]]; then
  "$ROOT/.venv/bin/python3" -m playwright install chromium
elif command -v uv >/dev/null 2>&1; then
  (cd "$ROOT" && uv run python -m playwright install chromium)
else
  echo "Warning: .venv not found. Run 'uv sync' first, then re-run this script for Loyverse Playwright." >&2
fi

echo ""
echo "Automations ready."
echo "  Loyverse Chrome: --user-data-dir=\"$LOYVERSE_ROOT/chrome-profile\""
echo "  Rede downloads:  \${REDE_DOWNLOAD_DIR:-\$HOME/Downloads/Rede}"
