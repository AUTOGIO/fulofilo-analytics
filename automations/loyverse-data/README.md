# Loyverse data root (bundled)

Local storage for Loyverse goods-report exports used by `app/utils/loyverse_automation.py`.

Default location after clone: `automations/loyverse-data/` in the fulofilo-analytics repo.

## Directories

| Directory | Contents |
|-----------|----------|
| `raw/` | Original Loyverse export files (CSV/XLSX/PDF) |
| `processed/` | Normalized CSV ready for Excel import |
| `logs/` | JSONL run logs (gitignored) |
| `chrome-profile/` | Dedicated Chrome user data for CDP automation (gitignored) |

Override with `LOYVERSE_DATA_ROOT` if you keep data elsewhere.

## Chrome for automation

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$LOYVERSE_DATA_ROOT/chrome-profile"
```

Set `LOYVERSE_DATA_ROOT` to this folder (or omit it when running from the default bundled path).
