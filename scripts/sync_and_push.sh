#!/usr/bin/env bash
# ============================================================
# FulôFiló — Sync Excel → validate → git commit → push
# ============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SYNC_SCRIPT="$REPO_ROOT/scripts/sync_excel.sh"
VALIDATE_SCRIPT="$REPO_ROOT/scripts/validate_generated_data.sh"
PY="$REPO_ROOT/.venv/bin/python3"
EXCEL_MASTER="$REPO_ROOT/data/excel/FuloFilo_Master.xlsx"
PARQUET_DIR="$REPO_ROOT/data/parquet"
CATALOG_CSV="$REPO_ROOT/data/raw/catalogs/product_catalog.csv"
GITHUB_HTTPS="https://github.com/AUTOGIO/fulofilo-analytics.git"

DRY_RUN=false
WITH_TESTS=false

CANONICAL_PARQUETS=(
  cashflow
  daily_sales
  inventory
  products
  profit_report
  quantity_report
  revenue_report
)

LEGACY_PARQUETS=(
  products_2024
  products_2026
  products_2026_03
  products_2026_04
)

log() {
  echo "[sync_and_push] $*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

usage() {
  cat <<'EOF'
Usage: bash scripts/sync_and_push.sh [--dry-run] [--with-tests]

  --dry-run     Run sync + validation and show what would be committed (no commit/push)
  --with-tests  After validation, run pytest tests/test_pipeline.py -q
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --with-tests)
      WITH_TESTS=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
done

cd "$REPO_ROOT"

log "Repo root: $REPO_ROOT"

if ! git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  fail "Not a git repository: $REPO_ROOT"
fi

if [[ -d "$REPO_ROOT/.git/rebase-merge" || -d "$REPO_ROOT/.git/rebase-apply" ]]; then
  fail "Git rebase in progress. Resolve it before syncing."
fi

if [[ -f "$REPO_ROOT/.git/MERGE_HEAD" ]]; then
  fail "Git merge in progress. Resolve it before syncing."
fi

current_branch="$(git -C "$REPO_ROOT" branch --show-current || true)"
if [[ -z "$current_branch" ]]; then
  fail "Detached HEAD detected. Checkout a branch before syncing."
fi

if [[ ! -f "$EXCEL_MASTER" ]]; then
  fail "Excel master not found: $EXCEL_MASTER"
fi

if [[ ! -f "$SYNC_SCRIPT" ]]; then
  fail "Sync script not found: $SYNC_SCRIPT"
fi

if [[ ! -x "$PY" ]]; then
  fail "venv missing. Run: cd $REPO_ROOT && uv sync"
fi

log "Running Excel sync..."
bash "$SYNC_SCRIPT"

log "Running generated-data validation..."
bash "$VALIDATE_SCRIPT"

if [[ "$WITH_TESTS" == true ]]; then
  log "Running pytest (tests/test_pipeline.py)..."
  if command -v uv >/dev/null 2>&1; then
    uv run pytest tests/test_pipeline.py -q
  else
    "$PY" -m pytest tests/test_pipeline.py -q
  fi
fi

stage_paths=()
stage_paths+=("$EXCEL_MASTER")
stage_paths+=("$CATALOG_CSV")

for name in "${CANONICAL_PARQUETS[@]}"; do
  stage_paths+=("$PARQUET_DIR/${name}.parquet")
done

for name in "${LEGACY_PARQUETS[@]}"; do
  legacy_file="$PARQUET_DIR/${name}.parquet"
  if [[ -f "$legacy_file" ]]; then
    stage_paths+=("$legacy_file")
  fi
done

existing_paths=()
for path in "${stage_paths[@]}"; do
  if [[ -f "$path" ]]; then
    existing_paths+=("$path")
  fi
done

if [[ ${#existing_paths[@]} -eq 0 ]]; then
  fail "No generated artifacts found to stage."
fi

log "Staging ${#existing_paths[@]} file(s)..."
git add -- "${existing_paths[@]}"

staged_lines="$(git diff --cached --name-only)"
if [[ -z "$staged_lines" ]]; then
  log "Nothing to commit — generated read models are already up to date."
  exit 0
fi

staged_count="$(printf '%s\n' "$staged_lines" | sed '/^$/d' | wc -l | tr -d ' ')"
log "$staged_count file(s) changed:"
git diff --cached --stat

if [[ "$DRY_RUN" == true ]]; then
  log "[DRY RUN] Would commit with message: data sync: $(date '+%Y-%m-%d %H:%M')"
  log "[DRY RUN] Would push to origin $current_branch"
  if [[ "$current_branch" != "main" ]]; then
    log "[DRY RUN] WARN: Streamlit Cloud typically deploys from main; pushing '$current_branch' may not redeploy cloud."
  fi
  log "[DRY RUN] Staged files:"
  git diff --cached --name-only
  exit 0
fi

commit_msg="data sync: $(date '+%Y-%m-%d %H:%M')"
log "Committing: $commit_msg"
if ! git commit -m "$commit_msg"; then
  if git diff --cached --quiet; then
    log "Nothing to commit after staging."
    exit 0
  fi
  fail "git commit failed."
fi

git remote set-url origin "$GITHUB_HTTPS" 2>/dev/null || true

log "Pushing to origin $current_branch..."
if ! git push origin "$current_branch"; then
  fail "git push failed. Check credentials (macOS Keychain / gh auth login)."
fi

if [[ "$current_branch" != "main" ]]; then
  log "WARN: Pushed to '$current_branch'. Streamlit Cloud typically deploys from main — cloud may not update."
fi

log "Push complete. Streamlit Cloud redeploys in ~60s."
log "https://autogio-fulofilo.streamlit.app/"
