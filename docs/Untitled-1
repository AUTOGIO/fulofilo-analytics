---
name: fulofilo-analytics-pro
description: This skill should be used when operating, maintaining, monitoring, syncing, launching, testing, or safely changing FulôFiló Analytics Pro in /Users/giovannini_nuovo/Documents/GitHub/FuloFilo. It enforces the local-first retail analytics data contract, source-of-truth rules, safe commands, and escalation boundaries for the Streamlit, DuckDB, Parquet, Excel, and openpyxl workflow.
version: 1.0.0
---

# FulôFiló Analytics Pro Operations

Operate as the project-specific AI agent for FulôFiló Analytics Pro, a local-first retail analytics dashboard on macOS Apple Silicon.

Primary project root:

`/Users/giovannini_nuovo/Documents/GitHub/FuloFilo`

Core principle: read before writing, confirm before deleting, and ask before changing code or business data.

## When to Use

Use this skill for requests involving FulôFiló Analytics Pro, including:

- Launching or stopping the dashboard
- Syncing Excel data into analytical read models
- Checking system health, tests, logs, or runtime status
- Investigating ETL, Streamlit, DuckDB, Parquet, Excel export, or audit-log behavior
- Making any project-specific code or workflow change

## Hard Limits

Never directly modify these files:

| File | Rule |
|------|------|
| `data/excel/FuloFilo_Master.xlsx` | Single canonical source of truth. Do not edit directly. |
| `data/parquet/*.parquet` | Generated artifacts. Only sync/app modules should write them. |
| `data/fulofilo.duckdb` | Live database. Do not delete, move, or open with another process while dashboard is running. |
| `data/logs/stock_audit.csv` | Append-only audit trail. Never edit or delete. |
| `excel/FuloFilo_Report_*.xlsx` | Read-only report outputs. Never use as operational write targets. |
| `app/pages/0*.py` | Dashboard pages. Do not modify unless explicitly instructed. |
| `app/db.py` | Core query engine. Do not modify unless explicitly instructed. |
| `pyproject.toml` | Dependency manifest. Modify only when explicitly asked to add/remove packages. |

Never run these unsupervised:

```bash
uv sync
python scripts/bootstrap_excel_master.py
rm -rf data/
git push --force
git reset --hard
```

## Data Contract

Treat `data/excel/FuloFilo_Master.xlsx` as the only operational source of truth.

Primary sheets:

- Catalog
- Inventory
- DailySales
- Cashflow
- CategoryOverrides
- Meta
- Daily Ops

Data flow:

```text
Excel Master -> scripts/sync_excel.sh -> scripts/sync_excel.py -> data/parquet/*.parquet -> DuckDB views -> Streamlit dashboard -> Excel reports
```

Write-back contract:

- `app/utils/inventory_ops.py::sync_to_excel()` writes stock levels back to the master workbook Inventory sheet columns D-F only.
- `app/utils/sales_ops.py::sync_csv_to_excel_daily_ops()` writes aggregated daily sales to the master workbook Daily Ops sheet.
- Runtime write-back must never target generated report files under `excel/`.

## Safe Commands

Run commands from the project root:

```bash
cd /Users/giovannini_nuovo/Documents/GitHub/FuloFilo
```

Launch dashboard:

```bash
bash scripts/launch_app.sh
```

Sync after Excel edits:

```bash
bash scripts/sync_excel.sh
```

Full refresh:

```bash
bash scripts/refresh_data.sh
```

Check dashboard status:

```bash
pgrep -fl streamlit
```

Stop dashboard:

```bash
pkill -f "streamlit run"
```

Run project health test:

```bash
.venv/bin/python3 -m pytest tests/test_pipeline.py -v
```

View recent stock audit entries:

```bash
tail -20 data/logs/stock_audit.csv
```

Rebuild the environment only if broken and after approval:

```bash
uv sync
```

Push code only after user asks for it:

```bash
git add -A
git commit -m "describe the change here"
git push origin main
```

## Daily Operations Workflow

When the operator asks to update inventory, sales, or data:

1. Confirm the Excel master has been edited and saved.
2. Confirm the dashboard is not actively being used if a sync could disrupt work.
3. Verify `data/excel/FuloFilo_Master.xlsx` exists.
4. Run `bash scripts/sync_excel.sh` from the project root.
5. Check output for validation errors.
6. If validation fails, report the exact error and do not directly fix the workbook unless explicitly instructed.
7. If sync succeeds, confirm that data has synced and the dashboard reflects the new data.

Stock adjustments through dashboard page 03 write back automatically to the master workbook and append to `data/logs/stock_audit.csv`.

Daily sales entries through dashboard page 04 sync aggregated sales back to the master workbook Daily Ops sheet.

## Code Change Workflow

For non-trivial code or ETL work:

1. Inspect relevant files first.
2. Explain the objective or root cause.
3. Propose the minimal implementation plan.
4. Apply the smallest safe change.
5. Validate syntax, imports, paths, data contract compatibility, and likely UI impact.
6. Summarize changed files, exact fix, risks, and how to test.

## Escalation Points

Stop and ask before:

- Any `git reset`, `git rebase`, or `git push --force`
- Deleting any file not in `data/parquet/` or `__pycache__`
- Modifying any `.py` file in `app/` or `core/`
- Running `scripts/bootstrap_excel_master.py`
- Installing or removing packages with `uv`, `pip`, or another package manager
- Any direct operation on `data/excel/FuloFilo_Master.xlsx`
- Any edit to `data/logs/stock_audit.csv`
- Any schema or structural database change
- Modifying or deleting `excel/FuloFilo_Report_*.xlsx`

## Final Response Pattern

When fixing bugs, return:

1. Root cause
2. Files changed
3. Exact fix
4. Risks
5. How to test

When building features, return:

1. Goal
2. Minimal implementation
3. Files edited
4. Validation steps
5. Future optional enhancements
