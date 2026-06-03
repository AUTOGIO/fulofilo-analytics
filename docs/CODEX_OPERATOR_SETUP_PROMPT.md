# Codex Prompt — FulôFiló Operator Setup (macOS, non-developer)

Copy everything inside the fenced block below into **Codex** (or Desktop Commander) as a single task. Do not ask the operator technical questions unless a step is impossible after automatic repair.

---

## PROMPT (copy from here)

```text
You are installing FulôFiló Analytics for a NON-DEVELOPER operator on macOS.

## Operator profile
- MacBook Air M3, macOS 26.6 (Apple Silicon)
- GitHub Desktop is installed
- No terminal skills; ALL steps must run automatically
- Language for user-facing messages: Brazilian Portuguese (simple words)

## Goal
1. Clone https://github.com/AUTOGIO/fulofilo-analytics (if not already present)
2. Install every missing dependency automatically (uv, Python venv, Node/npm, Playwright, Chrome check, Xcode CLT for Swift app)
3. Launch BOTH dashboards:
   - Streamlit web dashboard → http://127.0.0.1:8501
   - Native macOS FF Terminal → build and run macos/FuloFiloTerminal
4. Open the interactive Guided Assistance wizard → http://127.0.0.1:8502
5. Leave all three running; notify the operator in Portuguese what opened

## Canonical repo path (prefer this)
~/Documents/GitHub/fulofilo-analytics

If GitHub Desktop cloned elsewhere, detect the folder that contains FuloFiloOperatorSetup.command and set:
export FULOFILO_REPO="<that absolute path>"

## Execution plan (run in order, fix failures yourself)

### A. Locate or clone repository
- If ~/Documents/GitHub/fulofilo-analytics/.git exists → use it
- Else if GitHub Desktop clone exists under ~/Documents/GitHub/ → use that folder name
- Else: git clone https://github.com/AUTOGIO/fulofilo-analytics.git ~/Documents/GitHub/fulofilo-analytics

### B. Bootstrap (automatic install)
cd "$FULOFILO_REPO"  # or detected path
chmod +x scripts/*.sh FuloFiloOperatorSetup.command FuloFilo.command 2>/dev/null || true
export FULOFILO_REPO="$(pwd)"
bash scripts/operator_bootstrap.sh

This script MUST:
- Install uv via https://astral.sh/uv/install.sh if missing
- Run uv sync (recreate .venv if broken)
- Install Node via brew if npm missing (brew install node)
- Run scripts/setup_automations.sh
- Run scripts/sync_excel.sh when FuloFilo_Master.xlsx exists
- Write data/.operator_setup_complete

If any step fails, diagnose and retry (do not stop):
- xcode-select --install  → if swift build fails (FF Terminal)
- brew install node       → if npm missing and no node
- uv sync                 → if streamlit missing
- .venv/bin/python3 -m playwright install chromium

### C. Launch operator desktop (one command)
bash scripts/launch_operator_desktop.sh

This MUST:
- Start Streamlit app/app.py on port 8501 (background)
- Build macos/FuloFiloTerminal with scripts/build_macos_terminal.sh if needed, then run binary
- Start tools/guided_assistance/app.py on port 8502 (background)
- open http://127.0.0.1:8501 and http://127.0.0.1:8502 in default browser

Alternative for operator (Finder double-click):
./FuloFiloOperatorSetup.command

### D. Verify (report to operator)
- curl -sf http://127.0.0.1:8501 → OK dashboard
- curl -sf http://127.0.0.1:8502 → OK guided assistance
- pgrep -fl FuloFiloTerminal → OK native app (if Swift built)
- test -f data/.operator_setup_complete → OK bootstrap

### E. Guided assistance behavior
The wizard at :8502 is INTERACTIVE (Portuguese):
- Questions about Loyverse/Rede experience
- Step-by-step Chrome Loyverse setup
- Buttons to trigger Loyverse download and Rede Terminal launch
- Metrics quiz and navigation quiz
- Final tips

Tell the operator:
"Você verá três coisas: o painel no navegador (8501), o Assistente Guiado (8502) e o FF Terminal no Mac. Siga o Assistente — ele faz perguntas e ensina a baixar Loyverse e Rede."

## Hard rules
- NEVER ask the operator to edit code or JSON
- NEVER require manual pip/npm except if automatic install failed after 2 retries — then install yourself
- NEVER commit secrets; Rede uses macOS Keychain only
- Do NOT stop at warnings (Chrome missing, Swift build fail) — still open Streamlit + Guided Assistance and explain what is skipped in Portuguese

## Reference files in repo
- docs/AUTOMATIONS_USER_GUIDE.md — error solutions
- docs/CODEX_OPERATOR_SETUP_PROMPT.md — this prompt
- scripts/operator_bootstrap.sh
- scripts/launch_operator_desktop.sh
- tools/guided_assistance/app.py

## Done message (Portuguese, show to operator)
"Instalação concluída. Abri o dashboard, o assistente guiado e o FF Terminal. Comece pelo Assistente na aba que abriu (porta 8502). Se precisar abrir de novo, clique duas vezes em FuloFiloOperatorSetup.command na pasta do projeto."
```

---

## For humans (after Codex runs)

| Action | How |
|--------|-----|
| Run again later | Double-click `FuloFiloOperatorSetup.command` |
| Streamlit only | Double-click `FuloFilo.command` |
| Full docs | [AUTOMATIONS_USER_GUIDE.md](AUTOMATIONS_USER_GUIDE.md) |

## Ports

| Port | Service |
|------|---------|
| 8501 | Main Streamlit dashboard |
| 8502 | Guided Assistance wizard |
| 9222 | Chrome remote debugging (Loyverse) |
