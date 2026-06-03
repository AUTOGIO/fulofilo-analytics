#!/usr/bin/env bash
# Double-click in Finder — installs (if needed) and opens dashboards + guided tour.
set -euo pipefail
PROJECT="$(cd "$(dirname "$0")" && pwd)"
[ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env" 2>/dev/null || true
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export FULOFILO_REPO="$PROJECT"
osascript -e 'display notification "Instalando e abrindo FulôFiló…" with title "FulôFiló"'
bash "$PROJECT/scripts/launch_operator_desktop.sh"
echo ""
echo "Pressione Enter para fechar esta janela."
read -r _
