# FulôFiló Analytics

Local retail intelligence: Excel master → sync → Parquet/DuckDB → Streamlit terminal.

## Run

```bash
uv sync
bash scripts/sync_excel.sh
bash scripts/launch_app.sh
# or double-click FuloFilo.command
```

App: http://127.0.0.1:8501 · First-time Mac setup: double-click `FuloFiloOperatorSetup.command`

## Where things live

| Path | What |
|------|------|
| `data/excel/FuloFilo_Master.xlsx` | Source of truth (edit in Excel) |
| `app/` | Streamlit dashboard |
| `scripts/` | Sync, launch, automation helpers |
| `config/` | Non-secret settings |
| `docs/` | Guides · `docs/prompts/` for AI prompts |
| `assets/` | Brand + product images |
| `archive/` | Old / obsolete files (not deleted) |

More: [`docs/README.md`](docs/README.md) · Agent rules: [`AGENTS.md`](AGENTS.md)
