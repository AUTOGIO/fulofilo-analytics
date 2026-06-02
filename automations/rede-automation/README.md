# Rede automation (bundled)

Playwright automation for the Rede merchant portal. Lives inside [fulofilo-analytics](https://github.com/AUTOGIO/fulofilo-analytics) at `automations/rede-automation/`.

## Setup

From the **repository root**:

```bash
bash scripts/setup_automations.sh
```

Or from this directory:

```bash
npm install
npx playwright install chromium
```

## Credentials (macOS Keychain)

```bash
security add-generic-password -a "rede-email" -s "rede-automation-email" -w "YOUR_EMAIL_HERE" -U
security add-generic-password -a "rede-password" -s "rede-automation-password" -w "YOUR_PASSWORD_HERE" -U
```

## Usage

```bash
npm run rede:vendas -- --today
npm run rede:vendas -- --yesterday
npm run rede:vendas -- --date 2026-05-23
npm run rede:vendas -- --date 2026-05-23 --formats csv,excel,pdf
```

Paths resolve from this folder unless overridden:

- `REDE_AUTOMATION_ROOT` — project root (default: this directory)
- `REDE_DOWNLOAD_DIR` — download folder (default: `~/Downloads/Rede`)
- Browser profile: `.browser-profile/` (gitignored)
- Logs: `logs/` (gitignored)
