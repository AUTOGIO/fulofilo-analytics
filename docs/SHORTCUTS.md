# FulôFiló — macOS Shortcuts Integration

Use Shortcuts as an optional local trigger layer.  
Do not embed business rules in Shortcuts.

## Recommended pattern

Shortcuts triggers the local automation webhook, which executes Python actions:

- `refresh-dashboard-data`
- `generate-replenishment-alerts`
- `export-reports`
- `validate-data-integrity`

## 1. Start local webhook bridge

```bash
cd /Users/giovannini_nuovo/Library/Mobile Documents/com~apple~CloudDocs/Documents/GitHub/fulofilo-analytics
export FULOFILO_AUTOMATION_TOKEN="change-this-token"
make automation-webhook
```

## 2. Create a Shortcut

Open **Shortcuts.app** and create `Fulofilo Refresh`.

Add these actions:

1. **Text** (JSON body):
```json
{"action":"refresh-dashboard-data","idempotency_key":"shortcuts-refresh-001"}
```
2. **Get Contents of URL**
   - URL: `http://127.0.0.1:8787/run`
   - Method: `POST`
   - Request Body: `JSON` using the Text output
   - Header: `X-Automation-Token: change-this-token`
3. **Show Notification**: `FulôFiló refresh finished`

## 3. Optional schedule

Use Personal Automation in Shortcuts (`Time of Day`) to run this Shortcut.

## 4. Manual commands

```bash
make automation-refresh-dashboard-data
make automation-generate-replenishment-alerts
make automation-export-reports
make automation-validate-data-integrity
```

## Security note

Keep `FULOFILO_AUTOMATION_TOKEN` local and private.  
Do not hardcode real tokens in committed files.
