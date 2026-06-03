#!/usr/bin/env bash
set -euo pipefail
PROJECT="$(cd "$(dirname "$0")" && pwd)"
[ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env" 2>/dev/null || true
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
osascript -e 'display notification "Abrindo Assistente FulôFiló…" with title "FulôFiló FF"'
bash "$PROJECT/scripts/launch_guided_assistance.sh"
echo ""
echo "Pressione Enter para fechar."
read -r _
