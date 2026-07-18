# FulôFiló n8n Orchestration

n8n is the **external control plane** only (scheduling, triggers, ordering, retries).
All business logic stays in Python under this repository.

## Quick start

```bash
cd /Users/giovannini_nuovo/Library/Mobile Documents/com~apple~CloudDocs/Documents/GitHub/fulofilo-analytics
docker compose -f docker-compose.n8n.yml up -d
export FULOFILO_AUTOMATION_TOKEN="change-this-token"
make automation-webhook
```

- n8n UI: http://localhost:5678
- Webhook bridge: http://127.0.0.1:8787

## Import workflow

Import `docs/n8n/fulofilo_orchestration_workflow.json` in the n8n UI.

## Webhook contract

**Health:** `GET /health`

**Run:** `POST /run` with JSON body:

```json
{
  "action": "run-daily-automation",
  "idempotency_key": "daily-2026-06-01",
  "params": { "sku_policy": "balanced" }
}
```

Header: `X-Automation-Token: <token>` or `Authorization: Bearer <token>`

### Supported actions

| Action | Description |
|--------|-------------|
| `refresh-dashboard-data` | Sync Excel → parquet |
| `sync-excel-master` | Same as refresh |
| `generate-replenishment-alerts` | Reorder JSON + macOS notify |
| `generate-daily-briefing` | Morning digest + macOS notify |
| `export-reports` | Excel + ABC reports |
| `validate-data-integrity` | Strict sync + pytest |
| `run-daily-automation` | Full daily routine |

## Operational artifacts

- `data/outputs/replenishment_alerts.json` — explainable reorder alerts
- `data/outputs/daily_briefing.json` — executive morning digest
- `data/logs/ops_events.jsonl` — operational timeline
- `data/logs/ops_decisions.csv` — alert → action tracking (via `core.ops_memory.log_decision`)
