#!/bin/zsh
# ──────────────────────────────────────────────────────────────────────────────
# FulôFiló — Install Sales Drop Watcher
# Renders com.fulofilo.saleswatch.plist.in → ~/Library/LaunchAgents/ and loads it.
# Usage: bash scripts/launchagent/install_saleswatch.sh
#
# Optional: copy saleswatch.local.env.example → saleswatch.local.env (gitignored)
# and set FULOFILO_ROOT and/or SALESWATCH_PYTHON.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

LABEL="com.fulofilo.saleswatch"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLIST_TEMPLATE="$SCRIPT_DIR/${LABEL}.plist.in"
PLIST_DEST="$HOME/Library/LaunchAgents/${LABEL}.plist"

if [[ -f "$SCRIPT_DIR/saleswatch.local.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$SCRIPT_DIR/saleswatch.local.env"
  set +a
fi

REPO_ROOT="${FULOFILO_ROOT:-$REPO_ROOT}"
INCOMING="$REPO_ROOT/data/incoming"
LOGS="$REPO_ROOT/logs"

DEFAULT_PYTHON="$REPO_ROOT/.venv/bin/python"
if [[ -n "${SALESWATCH_PYTHON:-}" ]]; then
  PYTHON_BIN="$SALESWATCH_PYTHON"
elif [[ -x "$DEFAULT_PYTHON" ]]; then
  PYTHON_BIN="$DEFAULT_PYTHON"
else
  PYTHON_BIN="$(command -v python3)"
fi

PATH_VALUE="${SALESWATCH_PATH:-$REPO_ROOT/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin}"

echo "FulôFiló — Sales Drop Watcher Installer"
echo "========================================"
echo "Repo root : $REPO_ROOT"
echo "Python    : $PYTHON_BIN"

if [[ ! -f "$PLIST_TEMPLATE" ]]; then
  echo "❌ Missing template: $PLIST_TEMPLATE" >&2
  exit 1
fi

# 1 — Create folders
mkdir -p "$INCOMING"
mkdir -p "$LOGS"
echo "✅ Folders ready"
echo "   Drop zone : $INCOMING"
echo "   Logs      : $LOGS"

# 2 — Unload existing agent if already installed
if launchctl list 2>/dev/null | grep -q "$LABEL"; then
    launchctl bootout "gui/$(id -u)" "$PLIST_DEST" 2>/dev/null || launchctl unload "$PLIST_DEST" 2>/dev/null || true
    echo "✅ Unloaded existing agent"
fi

# 3 — Render plist (Python avoids sed delimiter/escape issues in paths)
PATH_VALUE="$PATH_VALUE" REPO_ROOT="$REPO_ROOT" PYTHON_BIN="$PYTHON_BIN" \
HOME="$HOME" PLIST_TEMPLATE="$PLIST_TEMPLATE" PLIST_DEST="$PLIST_DEST" \
python3 - <<'PY'
import os
from pathlib import Path

repo = os.environ["REPO_ROOT"]
py = os.environ["PYTHON_BIN"]
home = os.environ["HOME"]
path_val = os.environ["PATH_VALUE"]
src = Path(os.environ["PLIST_TEMPLATE"])
dst = Path(os.environ["PLIST_DEST"])
text = src.read_text(encoding="utf-8")
text = text.replace("@REPO_ROOT@", repo)
text = text.replace("@PYTHON_BIN@", py)
text = text.replace("@HOME@", home)
text = text.replace("@PATH_VALUE@", path_val)
dst.write_text(text, encoding="utf-8")
PY
echo "✅ Plist rendered → $PLIST_DEST"

# 4 — Load agent
launchctl bootstrap "gui/$(id -u)" "$PLIST_DEST" 2>/dev/null || launchctl load "$PLIST_DEST"
echo "✅ Agent loaded and active"

# 5 — Verify
if launchctl list 2>/dev/null | grep -q "$LABEL"; then
    echo ""
    echo "🟢 Watcher is ACTIVE"
    echo ""
    echo "  How to use:"
    echo "  1. Save any 'item-sales-summary-YYYY-MM-DD-YYYY-MM-DD.csv' to:"
    echo "     $INCOMING"
    echo "  2. The pipeline runs automatically (~10s later)"
    echo "  3. Streamlit redeploys in ~90 seconds"
    echo ""
    echo "  Watch live: tail -f $LOGS/saleswatch.log"
    echo "  Test now:   python scripts/sales_watcher.py --dry-run"
    echo ""
else
    echo "❌ Agent load failed — check:"
    echo "   plutil -lint $PLIST_DEST"
fi
