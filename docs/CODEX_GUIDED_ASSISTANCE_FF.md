# Codex Prompt — FulôFiló Guided Assistance (FF only)

Use this prompt when the repo is **already installed** and you only need to open the **interactive guided tour** (Loyverse, Rede, metrics, navigation).

For full clone + install + all dashboards, use [CODEX_OPERATOR_SETUP_PROMPT.md](CODEX_OPERATOR_SETUP_PROMPT.md).

---

## PROMPT (copy from here)

```text
You are opening the FulôFiló (FF) Guided Assistance for a NON-DEVELOPER on macOS.

## Scope (ONLY this task)
- Do NOT clone the repo unless it is missing entirely
- Do NOT run full operator bootstrap unless Python/Streamlit is broken
- Do NOT start port 8501 or FF Terminal unless the operator asks
- ONLY ensure and open: http://127.0.0.1:8502 (Assistente Guiado FF)

## Operator profile
- MacBook Air M3, macOS 26.6 (Apple Silicon)
- No developer skills; everything automatic
- User-facing messages: Brazilian Portuguese, simple words

## Find the repo
Preferred path: ~/Documents/GitHub/fulofilo-analytics

If missing, search for a folder containing:
- tools/guided_assistance/app.py
- FuloFiloGuidedAssistance.command

Then:
export FULOFILO_REPO="<absolute path>"
cd "$FULOFILO_REPO"

If repo does not exist anywhere:
git clone https://github.com/AUTOGIO/fulofilo-analytics.git ~/Documents/GitHub/fulofilo-analytics
cd ~/Documents/GitHub/fulofilo-analytics
uv sync

## Launch guided assistance (one command)
chmod +x scripts/launch_guided_assistance.sh FuloFiloGuidedAssistance.command 2>/dev/null || true
bash scripts/launch_guided_assistance.sh

This script MUST:
1. Ensure uv + .venv + streamlit exist (uv sync if needed)
2. Start tools/guided_assistance/app.py on port 8502 (background)
3. open http://127.0.0.1:8502 in the default browser

If port 8502 is already in use, open the URL anyway (do not start a duplicate).

## Fix failures automatically (do not ask the operator)
| Problem | Fix |
|---------|-----|
| uv missing | curl -fsSL https://astral.sh/uv/install.sh \| sh |
| streamlit missing | cd repo && uv sync |
| Port 8502 busy but dead | kill stale process, rerun launch script |
| curl fails after 30s | read logs/guided_assistance.log, fix, retry once |

## What the operator sees (port 8502)
Interactive 10-step wizard in Portuguese:
1. Bem-vindo
2. Seu perfil (Loyverse / Rede experience)
3. Dois painéis (Streamlit vs FF Terminal)
4. Loyverse — preparar Chrome (button opens Chrome profile)
5. Loyverse — baixar vendas (one-click download + Excel import)
6. Rede — credenciais (Keychain instructions)
7. Rede — baixar relatório (opens Terminal automation)
8. Entender os números (KPI quiz)
9. Navegação no sistema (where to click)
10. Dicas finais

The operator interacts with buttons and questions in the browser. You do NOT need to walk them through each step in chat — the app does that.

## Optional (only if operator asks)
- Main dashboard: bash scripts/launch_app.sh → http://127.0.0.1:8501
- Full desktop (8501 + 8502 + FF Terminal): bash scripts/launch_operator_desktop.sh

## Hard rules
- NEVER ask the operator to edit code
- NEVER paste long terminal commands to the operator — run them yourself
- NEVER store Rede passwords in files; Keychain only

## Verify
curl -sf http://127.0.0.1:8502 && echo "OK"

## Done message (Portuguese)
"Pronto! Abri o Assistente FulôFiló no navegador. Siga os passos na tela — ele ensina a baixar relatórios Loyverse e Rede e a entender os números. Para abrir de novo, clique duas vezes em FuloFiloGuidedAssistance.command na pasta do projeto."
```

---

## For humans

| Action | How |
|--------|-----|
| Double-click | `FuloFiloGuidedAssistance.command` |
| Terminal | `bash scripts/launch_guided_assistance.sh` |
| URL | http://127.0.0.1:8502 |
| Errors | [AUTOMATIONS_USER_GUIDE.md](AUTOMATIONS_USER_GUIDE.md) |

## Related

- App source: `tools/guided_assistance/app.py`
- Full install prompt: [CODEX_OPERATOR_SETUP_PROMPT.md](CODEX_OPERATOR_SETUP_PROMPT.md)
