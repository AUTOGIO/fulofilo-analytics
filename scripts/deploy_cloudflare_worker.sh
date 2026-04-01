#!/usr/bin/env bash
# Deploy Cloudflare Worker for dashboard.giovannini.us (redirect to Streamlit Cloud).
# Run from repo root after fixing Cloudflare: remove Tunnel public hostname + fix DNS (see below).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Optional: CLOUDFLARE_API_TOKEN — copy configs/cloudflare.deploy.env.example → .env.cloudflare
ENV_CF="$ROOT/.env.cloudflare"
if [[ -f "$ENV_CF" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_CF"
  set +a
fi

WORKER_JS="$ROOT/cf-worker/worker.js"
PLACEHOLDER="https://REPLACE_WITH_YOUR_STREAMLIT_URL.streamlit.app"

STREAMLIT_URL="${STREAMLIT_URL:-${1:-}}"

if [[ -z "$STREAMLIT_URL" ]]; then
  if grep -qF "$PLACEHOLDER" "$WORKER_JS"; then
    echo "Usage: STREAMLIT_URL=https://your-app.streamlit.app $0"
    echo "   or: $0 https://your-app.streamlit.app"
    exit 1
  fi
  echo "  (No URL passed; worker.js already has a non-placeholder URL — deploying as-is.)"
else
  sed -i '' "s|${PLACEHOLDER}|${STREAMLIT_URL}|g" "$WORKER_JS"
  echo "  ✅ worker.js → ${STREAMLIT_URL}"
fi

if grep -qF "$PLACEHOLDER" "$WORKER_JS"; then
  echo "  ❌ worker.js still contains the placeholder URL. Pass your Streamlit URL."
  exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo " Cloudflare dashboard (do this once if you had Error 1033 / Tunnel)"
echo "═══════════════════════════════════════════════════════════════════"
echo " 1. Zero Trust → Networks → Tunnels → remove public hostname"
echo "    dashboard.giovannini.us from any tunnel (or delete unused tunnel)."
echo " 2. DNS → giovannini.us: record for dashboard must NOT be *.cfargotunnel.com."
echo "    Use CNAME dashboard → giovannini.us or A/AAAA per your zone plan;"
echo "    proxy status ON (orange cloud) so the Worker route applies."
echo " 3. This script runs: wrangler deploy (routes from cf-worker/wrangler.toml)."
echo "═══════════════════════════════════════════════════════════════════"
echo ""

cd "$ROOT/cf-worker"
if ! command -v npx &>/dev/null; then
  echo "  ❌ npx not found. Install Node.js."
  exit 1
fi
WR_BIN=(npx wrangler)
if [[ -x "$ROOT/cf-worker/node_modules/.bin/wrangler" ]]; then
  WR_BIN=("$ROOT/cf-worker/node_modules/.bin/wrangler")
fi
echo "▶ wrangler deploy (${WR_BIN[*]})"
"${WR_BIN[@]}" deploy

echo ""
echo "  Done — https://dashboard.giovannini.us should redirect to Streamlit."
