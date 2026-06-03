#!/usr/bin/env bash
# Non-developer first-run: clone (if needed), install deps, automations, sync data.
set -euo pipefail

DEFAULT_REPO="$HOME/Documents/GitHub/fulofilo-analytics"
REPO="${FULOFILO_REPO:-$DEFAULT_REPO}"
REPO_URL="https://github.com/AUTOGIO/fulofilo-analytics.git"
MARKER="$REPO/data/.operator_setup_complete"
LOG="$REPO/logs/operator_bootstrap.log"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

mkdir -p "$(dirname "$LOG")" 2>/dev/null || true

# ── Shell PATH (uv, brew, nvm) ───────────────────────────────────────────────
[ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env" 2>/dev/null || true
[ -f "$HOME/.zprofile" ] && source "$HOME/.zprofile" 2>/dev/null || true
[ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc" 2>/dev/null || true
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    return 0
  fi
  log "Installing uv (Python toolchain)..."
  curl -fsSL https://astral.sh/uv/install.sh | sh
  [ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env" 2>/dev/null || true
  export PATH="$HOME/.local/bin:$PATH"
  command -v uv >/dev/null 2>&1
}

ensure_node() {
  if command -v npm >/dev/null 2>&1; then
    return 0
  fi
  if command -v brew >/dev/null 2>&1; then
    log "Installing Node.js via Homebrew..."
    brew install node
    return 0
  fi
  log "WARNING: npm not found. Install Node.js from https://nodejs.org/ (LTS), then re-run."
  return 1
}

ensure_chrome() {
  if [ -d "/Applications/Google Chrome.app" ]; then
    return 0
  fi
  log "WARNING: Google Chrome not found. Loyverse automation needs Chrome."
  return 1
}

clone_repo() {
  if [ -d "$REPO/.git" ]; then
    log "Repository already present at $REPO"
    return 0
  fi
  mkdir -p "$(dirname "$REPO")"
  log "Cloning $REPO_URL -> $REPO"
  if command -v gh >/dev/null 2>&1; then
    gh repo clone AUTOGIO/fulofilo-analytics "$REPO" || git clone "$REPO_URL" "$REPO"
  else
    git clone "$REPO_URL" "$REPO"
  fi
}

heal_venv() {
  cd "$REPO"
  local py="$REPO/.venv/bin/python3"
  if [ -x "$py" ] && "$py" -c "import streamlit" &>/dev/null 2>&1; then
    return 0
  fi
  log "Creating Python environment (uv sync)..."
  rm -rf "$REPO/.venv"
  uv sync
}

main() {
  log "=== FulôFiló operator bootstrap ==="
  clone_repo
  cd "$REPO"
  mkdir -p "$REPO/logs"

  ensure_uv || { log "Failed to install uv"; exit 1; }
  heal_venv
  ensure_node || true
  ensure_chrome || true

  log "Setting up Loyverse + Rede automations..."
  bash "$REPO/scripts/setup_automations.sh" >>"$LOG" 2>&1 || true

  if [ -f "$REPO/data/excel/FuloFilo_Master.xlsx" ]; then
    log "Syncing Excel master to dashboard data..."
    bash "$REPO/scripts/sync_excel.sh" >>"$LOG" 2>&1 || true
  else
    log "No Excel master yet — skip sync (run bootstrap_excel_master later if needed)."
  fi

  date -u +"%Y-%m-%dT%H:%M:%SZ" >"$MARKER"
  log "Bootstrap complete. Marker: $MARKER"
}

main "$@"
