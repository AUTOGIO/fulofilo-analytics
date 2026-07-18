# Local sales automations (Loyverse + Rede)

Bundled automations run from this repository after clone. No separate checkout of `rede-automation` or `loyverse-data` is required.

## Layout

| Path | Purpose |
|------|---------|
| `automations/loyverse-data/` | Loyverse exports, processed CSVs, Chrome profile, logs |
| `automations/rede-automation/` | Node + Playwright Rede portal downloader |

Override defaults with environment variables (optional):

```bash
export LOYVERSE_DATA_ROOT="/path/to/loyverse-data"
export REDE_AUTOMATION_ROOT="/path/to/rede-automation"
export REDE_DOWNLOAD_DIR="$HOME/Downloads/Rede"
```

## First-time setup (any machine)

From the repository root:

```bash
git clone https://github.com/AUTOGIO/fulofilo-analytics.git
cd fulofilo-analytics
uv sync
bash scripts/setup_automations.sh
```

`setup_automations.sh` creates Loyverse data folders, installs Rede npm dependencies, and installs Playwright Chromium for both Rede (Node) and Loyverse (Python `uv run playwright install chromium`).

## Loyverse (Chrome CDP)

1. Start Chrome with the Loyverse profile (leave the window open):

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$(pwd)/automations/loyverse-data/chrome-profile"
```

2. Log in to Loyverse in that window, then run:

```bash
.venv/bin/python3 scripts/automation_cli.py download-loyverse-daily-sales --date 2026-06-01
uv run python scripts/reconcile_loyverse_sales.py
bash scripts/sync_excel.sh
```

Drop a Loyverse **period export** (e.g. `item-sales-summary-2026-03-01-2026-06-19.csv`) in `data/incoming/`. Reconciliation runs automatically after daily Loyverse imports and during `make automation-run-daily`; you can also run it manually with the command above.

## Rede (macOS Keychain)

Store portal credentials once:

```bash
security add-generic-password -a "rede-email" -s "rede-automation-email" -w "YOUR_EMAIL" -U
security add-generic-password -a "rede-password" -s "rede-automation-password" -w "YOUR_PASSWORD" -U
```

Run from the repo (visible browser; complete CAPTCHA/2FA manually if prompted):

```bash
cd automations/rede-automation
npm run rede:vendas -- --yesterday
```

Or trigger from the FulôFiló automation CLI / dashboard:

```bash
.venv/bin/python3 scripts/automation_cli.py launch-rede-sales-download --date 2026-06-01
```

Downloads default to `~/Downloads/Rede`.

See also: [docs/AUTOMATIONS_USER_GUIDE.md](../docs/AUTOMATIONS_USER_GUIDE.md) (full user guide + troubleshooting).
