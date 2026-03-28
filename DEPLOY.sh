#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# FulôFiló — Deploy Script
# Run this ONCE from the project root after creating the GitHub repo.
# Usage: bash DEPLOY.sh
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

GITHUB_USER="autogio"
REPO_NAME="fulofilo-analytics"
DOMAIN="giovannini.us"
SUBDOMAIN="dashboard"

echo ""
echo "═══════════════════════════════════════"
echo " FulôFiló — Deploy Pipeline"
echo "═══════════════════════════════════════"

# ── STEP 1: GitHub ────────────────────────────────────────────────────────────
echo ""
echo "▶ STEP 1 — Push to GitHub"
echo ""

if ! git remote get-url origin &>/dev/null; then
  echo "  Creating remote origin → https://github.com/${GITHUB_USER}/${REPO_NAME}"
  git remote add origin "https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
else
  echo "  Remote already set: $(git remote get-url origin)"
fi

git add -A
git commit -m "chore: prepare for Streamlit Cloud deployment" 2>/dev/null || echo "  Nothing new to commit."
git push -u origin main

echo ""
echo "  ✅ Code pushed to GitHub."
echo ""
echo "  ─────────────────────────────────────────────────────────────────"
echo "  NEXT: Deploy on Streamlit Cloud (takes ~3 min):"
echo ""
echo "  1. Go to: https://share.streamlit.io"
echo "  2. Click 'New app'"
echo "  3. Repository : ${GITHUB_USER}/${REPO_NAME}"
echo "  4. Branch     : main"
echo "  5. Main file  : app/app.py"
echo "  6. Click 'Deploy'"
echo "  7. Copy the URL shown (e.g. https://autogio-fulofilo.streamlit.app)"
echo "  ─────────────────────────────────────────────────────────────────"
echo ""
read -rp "  Paste your Streamlit URL here and press Enter: " STREAMLIT_URL

if [[ -z "$STREAMLIT_URL" ]]; then
  echo "  ⚠️  No URL entered. Skipping Cloudflare Worker update."
  echo "     Edit cf-worker/worker.js manually and re-run: bash DEPLOY.sh"
  exit 0
fi

# ── STEP 2: Patch Worker URL ──────────────────────────────────────────────────
echo ""
echo "▶ STEP 2 — Updating Cloudflare Worker with Streamlit URL"
SCRIPT="cf-worker/worker.js"
sed -i '' "s|https://REPLACE_WITH_YOUR_STREAMLIT_URL.streamlit.app|${STREAMLIT_URL}|g" "$SCRIPT"
echo "  ✅ worker.js updated → ${STREAMLIT_URL}"

# ── STEP 3: Deploy Cloudflare Worker ─────────────────────────────────────────
echo ""
echo "▶ STEP 3 — Deploying Cloudflare Worker"
echo ""

if ! command -v wrangler &>/dev/null; then
  echo "  Installing wrangler..."
  npm install -g wrangler
fi

cd cf-worker
echo "  Authenticating with Cloudflare (browser will open)..."
npx wrangler login
echo ""
echo "  Deploying worker to ${SUBDOMAIN}.${DOMAIN}..."
npx wrangler deploy
cd ..

echo ""
echo "═══════════════════════════════════════"
echo " ✅ DONE — Share this link on WhatsApp:"
echo ""
echo "    https://${SUBDOMAIN}.${DOMAIN}"
echo ""
echo "═══════════════════════════════════════"
echo ""
